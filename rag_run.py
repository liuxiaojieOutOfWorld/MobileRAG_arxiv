import os
import time
import copy
import torch
import shutil
import subprocess
import json
from PIL import Image
import PIL.ImageDraw as ImageDraw
import atexit
import re
from datetime import datetime
from pathlib import Path

from MobileAgent.api import inference_chat
from MobileAgent.text_localization import ocr
from MobileAgent.icon_localization import det
from MobileAgent.controller import get_screenshot, tap, slide, type, back, home, slide_down
from MobileAgent.prompt import get_action_prompt, get_reflect_prompt, get_memory_prompt, get_process_prompt, get_planning_prompt
from MobileAgent.chat import init_action_chat, init_reflect_chat, init_memory_chat, add_response, add_response_two_image
#new added
from RAGS.rag import query_interrag, query_localrag, load_appname2pkg, query_memrag
import math

from RAGS.get_pkg import list_all_packages
from RAGS.check_install import load_existing_records, handle_new_installs
from plot import generate_html
from RAGS.memRAG import append_to_memrag_ndjson
from RAGS.FAISS_create import rag, _to_mem_documents

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from modelscope import snapshot_download, AutoModelForCausalLM, AutoTokenizer, GenerationConfig

from dashscope import MultiModalConversation

#new added(MEM_JSON, MEM_DIR)
from config import (
    ADB_PATH, API_URL, API_TOKEN, QWEN_API,
    CAPTION_CALL_METHOD, CAPTION_MODEL,
    LOCALRAG_DATA_FILE, INDEX_DIR,
    SCREENSHOT_DIR, RECORD_DIR, RECORD_SCREENSHOT_DIR, TEMP_DIR,
    REFLECTION_SWITCH, MEMORY_SWITCH, ADD_INFO, ADD_INFO_PLAN, MEM_JSON, MEM_DIR
)

import dashscope
import concurrent
import re, textwrap
import requests

####################################### Edit your Setting #########################################
# Your ADB path
adb_path = ADB_PATH

# Your instruction
instruction = "open Google Maps."

# # Your gpt-4-turbo API URL
API_url = API_URL

# Your gpt-4-turbo API Token
token = API_TOKEN

# Choose between "api" and "local". api: use the qwen api. local: use the local qwen checkpoint
caption_call_method = CAPTION_CALL_METHOD

# Choose between "qwen-vl-plus" and "qwen-vl-max" if use api method. Choose between "qwen-vl-chat" and "qwen-vl-chat-int4" if use local method.
caption_model = CAPTION_MODEL

# If you choose the api caption call method, input your Qwen api here
qwen_api = QWEN_API

# You can add operational knowledge to help Agent operate more accurately.
add_info = ADD_INFO
add_info_plan = ADD_INFO_PLAN
# Reflection Setting: If you want to improve the operating speed, you can disable the reflection agent. This may reduce the success rate.
reflection_switch = REFLECTION_SWITCH

# Memory Setting: If you want to improve the operating speed, you can disable the memory unit. This may reduce the success rate.
memory_switch = MEMORY_SWITCH

#JSON and FAISS for RAG
json_dir = str(LOCALRAG_DATA_FILE)  # JSON path
index_dir = str(INDEX_DIR)    # FAISS path
###################################################################################################


current_task_state = {
    "current_app": None,
    "task_completed": False,
    "next_app": None
}

def extract_pkg_from_text(text):
    try:
        pkg_pattern = r'"pkg":\s*"([^"]+)"'
        app_name_pattern = r'"app_name":\s*"([^"]+)"'
        
        pkg_matches = re.finditer(pkg_pattern, text)
        pkgs = []
        for match in pkg_matches:
            pkg = match.group(1)
            pkgs.append(pkg)
            print(f"[DEBUG] Find pkg: {pkg}")
        
        app_name_matches = re.finditer(app_name_pattern, text)
        app_names = []
        for match in app_name_matches:
            app_name = match.group(1)
            app_names.append(app_name)
            print(f"[DEBUG] Find app_name: {app_name}")
        
        if pkgs and app_names:
            # return the first
            return pkgs[0], app_names[0]
        return None, None
    except Exception as e:
        print(f"[WARN] Fail to find pkg and app_name: {str(e)}")
        return None, None

def get_all_files_in_folder(folder_path):
    file_list = []
    for file_name in os.listdir(folder_path):
        file_list.append(file_name)
    return file_list


def draw_coordinates_on_image(image_path, coordinates):
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    point_size = 10
    for coord in coordinates:
        draw.ellipse((coord[0] - point_size, coord[1] - point_size, coord[0] + point_size, coord[1] + point_size), fill='red')
    output_image_path = './rag_screenshot/output_image.png'
    image.save(output_image_path)
    return output_image_path


def crop(image, box, i):
    image = Image.open(image)
    x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    if x1 >= x2-10 or y1 >= y2-10:
        return
    cropped_image = image.crop((x1, y1, x2, y2))
    cropped_image.save(f"./temp/{i}.jpg")


def generate_local(tokenizer, model, image_file, query):
    query = tokenizer.from_list_format([
        {'image': image_file},
        {'text': query},
    ])
    response, _ = model.chat(tokenizer, query=query, history=None)
    return response



def process_image(image, query, max_retries=3):
    dashscope.api_key = qwen_api
    image = "file://" + image
    messages = [{
        'role': 'user',
        'content': [
            {
                'image': image
            },
            {
                'text': query
            },
        ]
    }]
    
    for attempt in range(max_retries):
        try:
            response = MultiModalConversation.call(
                model=caption_model, 
                messages=messages,
                timeout=5  
            )
            try:
                response = response['output']['choices'][0]['message']['content'][0]["text"]
            except:
                response = "This is an icon."
            return response
        except (requests.exceptions.SSLError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt == max_retries - 1:
                return "This is an icon."
            time.sleep(1)  
        except Exception as e:
            print(f"Wrong: {str(e)}")
            return "This is an icon."


def generate_api(images, query):
    icon_map = {}
    for i, image in enumerate(images):
        try:
            response = process_image(image, query)
            icon_map[i + 1] = response
        except Exception as e:
            print(f"Wrong in {i+1}: {str(e)}")
            icon_map[i + 1] = "This is an icon."
    
    return icon_map

def merge_text_blocks(text_list, coordinates_list):
    merged_text_blocks = []
    merged_coordinates = []

    sorted_indices = sorted(range(len(coordinates_list)), key=lambda k: (coordinates_list[k][1], coordinates_list[k][0]))
    sorted_text_list = [text_list[i] for i in sorted_indices]
    sorted_coordinates_list = [coordinates_list[i] for i in sorted_indices]

    num_blocks = len(sorted_text_list)
    merge = [False] * num_blocks

    for i in range(num_blocks):
        if merge[i]:
            continue
        
        anchor = i
        
        group_text = [sorted_text_list[anchor]]
        group_coordinates = [sorted_coordinates_list[anchor]]

        for j in range(i+1, num_blocks):
            if merge[j]:
                continue

            if abs(sorted_coordinates_list[anchor][0] - sorted_coordinates_list[j][0]) < 10 and \
            sorted_coordinates_list[j][1] - sorted_coordinates_list[anchor][3] >= -10 and sorted_coordinates_list[j][1] - sorted_coordinates_list[anchor][3] < 30 and \
            abs(sorted_coordinates_list[anchor][3] - sorted_coordinates_list[anchor][1] - (sorted_coordinates_list[j][3] - sorted_coordinates_list[j][1])) < 10:
                group_text.append(sorted_text_list[j])
                group_coordinates.append(sorted_coordinates_list[j])
                merge[anchor] = True
                anchor = j
                merge[anchor] = True

        merged_text = "\n".join(group_text)
        min_x1 = min(group_coordinates, key=lambda x: x[0])[0]
        min_y1 = min(group_coordinates, key=lambda x: x[1])[1]
        max_x2 = max(group_coordinates, key=lambda x: x[2])[2]
        max_y2 = max(group_coordinates, key=lambda x: x[3])[3]

        merged_text_blocks.append(merged_text)
        merged_coordinates.append([min_x1, min_y1, max_x2, max_y2])

    return merged_text_blocks, merged_coordinates


def get_perception_infos(adb_path, screenshot_file):
    get_screenshot(adb_path)
    width, height = Image.open(screenshot_file).size
    try:
        text, coordinates = ocr(screenshot_file, ocr_detection, ocr_recognition)
        text, coordinates = merge_text_blocks(text, coordinates)
    except Exception as e:
        print(f"OCR cannot find text : {e}")
        text, coordinates = [], []
    center_list = [[(coordinate[0]+coordinate[2])/2, (coordinate[1]+coordinate[3])/2] for coordinate in coordinates]
    draw_coordinates_on_image(screenshot_file, center_list)
    perception_infos = []
    for i in range(len(coordinates)):
        perception_info = {"text": "text: " + text[i], "coordinates": coordinates[i]}
        perception_infos.append(perception_info)
    coordinates = det(screenshot_file, "icon", groundingdino_model)
    for i in range(len(coordinates)):
        perception_info = {"text": "icon", "coordinates": coordinates[i]}
        perception_infos.append(perception_info)
    image_box = []
    image_id = []
    for i in range(len(perception_infos)):
        if perception_infos[i]['text'] == 'icon':
            image_box.append(perception_infos[i]['coordinates'])
            image_id.append(i)
    for i in range(len(image_box)):
        crop(screenshot_file, image_box[i], image_id[i])
    images = get_all_files_in_folder(temp_file)
    if len(images) > 0:
        images = sorted(images, key=lambda x: int(x.split('/')[-1].split('.')[0]))
        image_id = [int(image.split('/')[-1].split('.')[0]) for image in images]
        icon_map = {}
        prompt = 'This image is an icon from a phone screen. Please briefly describe the shape and color of this icon in one sentence.'
        if caption_call_method == "local":
            for i in range(len(images)):
                image_path = os.path.join(temp_file, images[i])
                icon_width, icon_height = Image.open(image_path).size
                if icon_height > 0.8 * height or icon_width * icon_height > 0.2 * width * height:
                    des = "None"
                else:
                    des = generate_local(tokenizer, model, image_path, prompt)
                icon_map[i+1] = des
        else:
            for i in range(len(images)):
                images[i] = os.path.join(temp_file, images[i])
            icon_map = generate_api(images, prompt)
        for i, j in zip(image_id, range(1, len(image_id)+1)):
            if icon_map.get(j):
                perception_infos[i]['text'] = "icon: " + icon_map[j]
    for i in range(len(perception_infos)):
        perception_infos[i]['coordinates'] = [int((perception_infos[i]['coordinates'][0]+perception_infos[i]['coordinates'][2])/2), int((perception_infos[i]['coordinates'][1]+perception_infos[i]['coordinates'][3])/2)]
    return perception_infos, width, height

def save_steps_json(current_steps, record_dir):
    try:
        steps_json_path = os.path.join(record_dir, "steps.json")
        #  UTF-8 save
        with open(steps_json_path, "w", encoding="utf-8") as f:
            json.dump(current_steps, f, ensure_ascii=False, indent=2)
        
        #make sure
        with open(steps_json_path, "r", encoding="utf-8") as f:
            content = f.read()
            if not content:
                raise Exception("steps.json is empty")
            json.loads(content)
            
        print("✅ steps.json saved successfully")
    except Exception as e:
        print(f"❌ error when saving steps.json: {e}")

def cleanup():
    try:
        if current_steps: 
            save_steps_json(current_steps, record_dir)
    except Exception as e:
        print(f"Error in cleanup: {str(e)}")







record_dir = RECORD_DIR #ROOT_DIR / "rag_records"
record_screenshot_dir = RECORD_SCREENSHOT_DIR # RECORD_DIR / "screenshots"
os.makedirs(record_dir, exist_ok=True)
os.makedirs(record_screenshot_dir, exist_ok=True) 
screenshot = "rag_screenshot"

temp_file = TEMP_DIR # ROOT_DIR / "temp"
if not os.path.exists(temp_file):
    os.mkdir(temp_file)
else:
    shutil.rmtree(temp_file)
    os.mkdir(temp_file)
if not os.path.exists(screenshot):
    os.mkdir(screenshot)
error_flag = False

step_id = 1 
current_steps = [] 
task_name = instruction.replace(" ", "_")[:30]
existing_pkgs, max_id = load_existing_records(json_dir)
seen_pkgs = set(list_all_packages(adb_path)) 


pattern = re.compile(r'Open\s+app\s*(?:\(\s*"?([^"\)]+)"?\s*\)|"?([^"\)]+)"?)')


print("remove old records...")
for file in os.listdir(record_screenshot_dir):
    file_path = os.path.join(record_screenshot_dir, file)
    try:
        if os.path.isfile(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f"❌ error when removing file {file_path}: {e}")


steps_json_path = os.path.join(record_dir, "steps.json")
if os.path.exists(steps_json_path):
    try:
        os.unlink(steps_json_path)
        print("✅ old steps.json file has been removed")
    except Exception as e:
        print(f"❌ error when removing steps.json file: {e}")

atexit.register(cleanup)


os.makedirs(record_dir, exist_ok=True)
os.makedirs(record_screenshot_dir, exist_ok=True)



device = "cuda"
torch.manual_seed(1234)
if caption_call_method == "local":
    if caption_model == "qwen-vl-chat":
        model_dir = snapshot_download('qwen/Qwen-VL-Chat')
        model = AutoModelForCausalLM.from_pretrained(model_dir, device_map=device, trust_remote_code=True).eval()
        model.generation_config = GenerationConfig.from_pretrained(model_dir, trust_remote_code=True)
    elif caption_model == "qwen-vl-chat-int4":
        qwen_dir = snapshot_download("qwen/Qwen-VL-Chat-Int4")
        model = AutoModelForCausalLM.from_pretrained(qwen_dir, device_map=device, trust_remote_code=True,use_safetensors=True).eval()
        model.generation_config = GenerationConfig.from_pretrained(qwen_dir, trust_remote_code=True, do_sample=False)
    else:
        print("If you choose local caption method, you must choose the caption model from \"Qwen-vl-chat\" and \"Qwen-vl-chat-int4\"")
        exit(0)
    tokenizer = AutoTokenizer.from_pretrained(qwen_dir, trust_remote_code=True)
elif caption_call_method == "api":
    pass
else:
    print("You must choose the caption model call function from \"local\" and \"api\"")
    exit(0)


### Load ocr and icon detection model ###

groundingdino_dir = snapshot_download('AI-ModelScope/GroundingDINO', revision='v1.0.0')
groundingdino_model = pipeline('grounding-dino-task', model=groundingdino_dir)
ocr_detection = pipeline(Tasks.ocr_detection, model='damo/cv_resnet18_ocr-detection-line-level_damo')
ocr_recognition = pipeline(Tasks.ocr_recognition, model='damo/cv_convnextTiny_ocr-recognition-document_damo')





   


iter = 0

mode = "planning"

def main():
    opened_memory = ""  
    rag_info = ""      
    memory = ""       
    add_info = ""      
    error_flag = False 
    keyboard = False   
    last_keyboard = False  
    last_perception_infos = []  
    perception_infos = []  
    thought_history = []  
    summary_history = []  
    action_history = []   
    current_steps = []    
    step_id = 1          
    iter = 1            
    mode = "planning"    
    current_task = ""    
    record_task = "" 
    decision = ""
    complete_task = ""
    existing_pkgs, max_id = load_existing_records(json_dir)
    

    completed_requirements = ""
    insight = ""
    add_info_plan = ""

    record_dir = RECORD_DIR

 
    mem_json = MEM_JSON
    mem_dir = MEM_DIR
    memrag = " "

    record_screenshot_dir = RECORD_SCREENSHOT_DIR
    temp_file = TEMP_DIR
    screenshot_record = ""  
    screenshot_file = "./rag_screenshot/screenshot.jpg"
    last_screenshot_file = "./rag_screenshot/last_screenshot.jpg"

    os.makedirs(record_dir, exist_ok=True)
    os.makedirs(record_screenshot_dir, exist_ok=True)
    os.makedirs(temp_file, exist_ok=True)
    
    summary = ""

 
    result = query_memrag(instruction, mem_dir, mem_json)
    print(result)
    score   = float(result["score"])                       
    actions = result["action"]                              
    task    = result["task"]                                
    EPS = 1e-6  

    if math.isclose(score, 0.0, abs_tol=EPS):
        print(f"✅ Match in MemRAG database")

        for action in actions:
            if "Query LocalRAG" in action:
                term = output_action.split("(", 1)[1].rsplit(")", 1)[0].strip().strip('"')
                print("output_action:", output_action)
                rag_text = query_localrag(term, index_dir, json_dir)                 
                rag_info += f"[LocalRAG result for \"{term}\"]\n{rag_text}\n"
                time.sleep(3)
                continue
                
                


            if "Query InterRAG" in action:
                term = output_action.split("(", 1)[1].rsplit(")", 1)[0].strip().strip('"')
                web_text = query_interrag(term)                 
                rag_info += f"[InterRAG query: \"{term}\"]\n{web_text}\n" 
                time.sleep(3)
                continue
                
                
            if "Open app" in action:
                m = pattern.search(action)
                if m:
                    app_name = m.group(1) if m.group(1) else m.group(2)
                else:
                    app_name = ''
                print(f"[DEBUG] App name: {app_name}")
                

                APP_MAP = load_appname2pkg(json_dir)
                pkg = APP_MAP.get(app_name.lower())
                if pkg:
                    print(f"✅ [INFO] Found package name in APP_MAP: {pkg}")
                    subprocess.run([adb_path, "shell", "monkey", "-p", pkg, "-c",
                                "android.intent.category.LAUNCHER", "1"],
                                check=False)
                    opened_memory += app_name + " "
                else:

                    memory_apps = opened_memory.split()
                    found_in_memory = False
                    for mem_app in memory_apps:
                        if app_name.lower() in mem_app.lower():
                            found_in_memory = True
                            full_app_name = mem_app
                            task_app = full_app_name
                            pkg = APP_MAP.get(full_app_name.lower())
                            if pkg:
                                print(f"✅ [INFO] Found package name in APP_MAP using full name: {pkg}")
                                subprocess.run([adb_path, "shell", "monkey", "-p", pkg, "-c",
                                            "android.intent.category.LAUNCHER", "1"],
                                            check=False)
                                
            if "Tap" in action:
                coordinate = action.split("(")[-1].split(")")[0].split(", ")
                x, y = int(coordinate[0]), int(coordinate[1])
                tap(adb_path, x, y)
            if "Swipe" in action:
                coordinate1 = action.split("Swipe (")[-1].split("), (")[0].split(", ")
                coordinate2 = action.split("), (")[-1].split(")")[0].split(", ")
                x1, y1 = int(coordinate1[0]), int(coordinate1[1])
                x2, y2 = int(coordinate2[0]), int(coordinate2[1])
                slide(adb_path, x1, y1, x2, y2)
                
            if "Type" in action:
                if "(text)" not in action:
                    text = action.split("(")[-1].split(")")[0]
                else:
                    text = action.split(" \"")[-1].split("\"")[0]
                type(adb_path, text)

                is_search = False

                for info in perception_infos:
                    if "search" in info['text'].lower() or "search" in info['text']:
                        is_search = True
                        break

                if is_search:
                    subprocess.run([adb_path, "shell", "input", "keyevent", "66"], check=False)  # 66 是回车键的 keycode
                    time.sleep(5)  
            
            if "Back" in action:
                back(adb_path)
            
            if "Home" in action:
                home(adb_path)
                
            if "Stop" in action:
                print(f"Done all actions in MemRAG")
            
            time.sleep(5)
                                    

    else:
        if 0 < score <= 0.2:
            memrag += f"{task}: {actions}\n"
            print(f"Similar Match in MemRAG database")

        if score > 0.2:
            print(f"❌ Not Match in MemRAG database")

        while True:
            if mode == "planning":
                screenshot_file = "./rag_screenshot/screenshot.jpg"

                prompt_plan = get_planning_prompt(
                    instruction,
                    summary_history,
                    action_history,
                    add_info_plan,
                    completed_requirements,
                    memory,
                    rag_info,
                    current_task, 
                    complete_task,
                    memrag
                )

                chat_action = init_action_chat()
                chat_action = add_response("user", prompt_plan, chat_action)

                output_action = inference_chat(chat_action, 'gpt-4.1', API_url, token)
                thought = output_action.split("### Thought ###")[-1].split("### Action ###")[0].replace("\n"," ").replace(":","").replace("  "," ").strip()
                action = output_action.split("### Action ###")[-1].split("### Operation ###")[0].replace("\n"," ").replace(":","").replace("  "," ").strip()
                summary = output_action.split("### Operation ###")[-1].replace("\n"," ").replace("  "," ").strip()
                chat_action = add_response("assistant", output_action, chat_action)
                print("#" * 50, "Planning", "#" * 50)
                print(output_action[:400] + ("…" if len(output_action) > 400 else ""))
                time.sleep(3)
                

                thought_history.append(thought)
                summary_history.append(summary)
                action_history.append(action)
                
                if memory_switch:
                    prompt_memory = get_memory_prompt(insight)
                    chat_action = add_response("user", prompt_memory, chat_action)
                    output_memory = inference_chat(chat_action, 'gpt-4.1', API_url, token)
                    chat_action = add_response("assistant", output_memory, chat_action)
                    status = "#" * 50 + " Memory " + "#" * 50
                    print(status)
                    print(output_memory)
                    print('#' * len(status))
                    output_memory = output_memory.split("### Important content ###")[-1].split("\n\n")[0].strip() + "\n"
                    if "None" not in output_memory and output_memory not in memory:
                        memory += output_memory

                get_screenshot(adb_path)
                screenshot_record = os.path.join(record_screenshot_dir, f"{step_id:04d}.jpg")
                shutil.copy2(screenshot_file, screenshot_record)         


                draft_action = {
                    "step_id"   : step_id,
                    "mode"      : "planning",
                    "thought"   : thought,
                    "operation" : summary,
                    "action"    : action,
                    "memory"    : output_memory,
                    "reflection": None,                 
                    "planning"  : None,                 
                    "screenshot": os.path.basename(screenshot_record)
                }
                current_steps.append(draft_action)
                save_steps_json(current_steps, record_dir)
                step_id += 1


                if "Query LocalRAG" in action:
                    term = output_action.split("(", 1)[1].rsplit(")", 1)[0].strip().strip('"')
                    print("output_action:", output_action)
                    rag_text = query_localrag(term, index_dir, json_dir)                 
                    rag_info += f"[LocalRAG result for \"{term}\"]\n{rag_text}\n"
                    time.sleep(3)
                    continue

                if "Query InterRAG" in action:
                    term = output_action.split("(", 1)[1].rsplit(")", 1)[0].strip().strip('"')
                    web_text = query_interrag(term)                 
                    rag_info += f"[InterRAG query: \"{term}\"]\n{web_text}\n" 
                    time.sleep(3)
                    continue


                if "Open app" in action:
                    m = pattern.search(action)
                    if m:
                        app_name = m.group(1) if m.group(1) else m.group(2)
                    else:
                        app_name = ''
                    print(f"[DEBUG] App name: {app_name}")
                    

                    APP_MAP = load_appname2pkg(json_dir)
                    pkg = APP_MAP.get(app_name.lower())
        
                    if pkg:
                        print(f"✅ [INFO] Found package name in APP_MAP: {pkg}")
                        subprocess.run([adb_path, "shell", "monkey", "-p", pkg, "-c",
                                    "android.intent.category.LAUNCHER", "1"],
                                    check=False)
                        opened_memory += app_name + " "
                    else:
                        
                        memory_apps = opened_memory.split()
                        found_in_memory = False
                        for mem_app in memory_apps:
                            if app_name.lower() in mem_app.lower():
                                found_in_memory = True
                                full_app_name = mem_app
                                task_app = full_app_name
                                pkg = APP_MAP.get(full_app_name.lower())
                                if pkg:
                                    print(f"✅ [INFO] Found package name in APP_MAP using full name: {pkg}")
                                    subprocess.run([adb_path, "shell", "monkey", "-p", pkg, "-c",
                                                "android.intent.category.LAUNCHER", "1"],
                                                check=False)
                                    break
                        
                        if not found_in_memory:
                            print(f"[WARN] app_name '{app_name}' not found in mapping or memory.")
                            
                            rag_text = query_localrag(app_name, index_dir, json_dir)
                            if rag_text:
                                try:        
                                    
                                    pkg, full_app_name = extract_pkg_from_text(rag_text)
                                    if pkg:
                                        print(f"✅ [INFO] Find: {pkg}")
                                        print(f"[INFO] Find: {full_app_name}")
                                        
                                        
                                        subprocess.run([adb_path, "shell", "monkey", "-p", pkg, "-c",
                                                    "android.intent.category.LAUNCHER", "1"],
                                                    check=False)
                                        
                                        if full_app_name:
                                            opened_memory += full_app_name + " "
                                            task_app = full_app_name
                                        else:
                                            opened_memory += app_name + " "
                                            task_app = app_name
                                    else:
                                        print("[WARN] Cant find app pkg and name")
                                except Exception as e:
                                    print(f"[WARN] Failed to process LocalRAG result: {str(e)}")
                                    import traceback
                                    print("[DEBUG] Deatils on invalid info:")
                                    print(traceback.format_exc())
                    mode = "interaction"


                if "Switch to Action Mode" in action:
                    mode = "interaction"
                    time.sleep(1)
                    continue

                time.sleep(5)
                continue

            else:  # interaction mode
                iter += 1


                screenshot_file = "./rag_screenshot/screenshot.jpg"
                perception_infos, width, height = get_perception_infos(adb_path, screenshot_file)
                shutil.rmtree(temp_file)
                os.mkdir(temp_file)
                screenshot_record = os.path.join(record_screenshot_dir, f"{step_id:04d}.jpg")
                shutil.copy2(screenshot_file, screenshot_record)

                keyboard = False
                keyboard_height_limit = 0.9 * height
                result = subprocess.run(f"{adb_path} shell dumpsys input_method | grep -E 'mInputShown'", shell=True, capture_output=True, text=True)
                if "mInputShown=true" in result.stdout:
                    keyboard = True
                else:
                    for perception_info in perception_infos:
                        if perception_info['coordinates'][1] < keyboard_height_limit:
                            continue
                        if 'ADB Keyboard' in perception_info['text']:
                            keyboard = True
                            break


                current_thought = f"Current operation: {summary}"
                temp_thought_history = thought_history + [current_thought]
                
                prompt_action = get_action_prompt(
                    instruction, 
                    perception_infos, 
                    width, 
                    height, 
                    keyboard,
                    temp_thought_history, 
                    summary_history, 
                    action_history, 
                    memory, 
                    add_info, 
                    decision,
                    current_task, 
                    complete_task,
                    memrag
                )
                chat_action = init_action_chat()
                chat_action = add_response("user", prompt_action, chat_action, screenshot_file)

                output_action = inference_chat(chat_action, 'gpt-4o', API_url, token)
                thought = output_action.split("### Thought ###")[-1].split("### Action ###")[0].replace("\n", " ").replace(":", "").replace("  ", " ").strip()
                summary = output_action.split("### Operation ###")[-1].replace("\n", " ").replace("  ", " ").strip()
                action = output_action.split("### Action ###")[-1].split("### Operation ###")[0].replace("\n", " ").replace("  ", " ").strip()
                chat_action = add_response("assistant", output_action, chat_action)
                status = "#" * 50 + " Decision " + "#" * 50
                print(status)
                print(output_action)
                print('#' * len(status))
                
                if memory_switch:
                    prompt_memory = get_memory_prompt(insight)
                    chat_action = add_response("user", prompt_memory, chat_action)
                    output_memory = inference_chat(chat_action, 'gpt-4.1', API_url, token)
                    chat_action = add_response("assistant", output_memory, chat_action)
                    status = "#" * 50 + " Memory " + "#" * 50
                    print(status)
                    print(output_memory)
                    print('#' * len(status))
                    output_memory = output_memory.split("### Important content ###")[-1].split("\n\n")[0].strip() + "\n"
                    if "None" not in output_memory and output_memory not in memory:
                        memory += output_memory
                
                draft_action = {
                    "step_id": step_id,
                    "mode": "action",
                    "thought": thought,
                    "operation": summary,
                    "action": action,
                    "memory": output_memory,
                    "reflection": None,
                    "planning": None,
                    "screenshot": os.path.basename(screenshot_record)
                }
                current_steps.append(draft_action)
                save_steps_json(current_steps, record_dir)
                step_id += 1
                if "Tap" in action:
                    coordinate = action.split("(")[-1].split(")")[0].split(", ")
                    x, y = int(coordinate[0]), int(coordinate[1])
                    tap(adb_path, x, y)
                elif "Swipe" in action:
                    coordinate1 = action.split("Swipe (")[-1].split("), (")[0].split(", ")
                    coordinate2 = action.split("), (")[-1].split(")")[0].split(", ")
                    x1, y1 = int(coordinate1[0]), int(coordinate1[1])
                    x2, y2 = int(coordinate2[0]), int(coordinate2[1])
                    slide(adb_path, x1, y1, x2, y2)
                    
                elif "Type" in action:
                    if "(text)" not in action:
                        text = action.split("(")[-1].split(")")[0]
                    else:
                        text = action.split(" \"")[-1].split("\"")[0]
                    type(adb_path, text)
         
                    is_search = False
                  
                    for info in perception_infos:
                        if "search" in info['text'].lower() or "搜索" in info['text']:
                            is_search = True
                            break
                    
                
                    if is_search:
                        subprocess.run([adb_path, "shell", "input", "keyevent", "66"], check=False)  # 66 是回车键的 keycode
                        time.sleep(5) 
                
                elif "Back" in action:
                    back(adb_path)
                
                elif "Home" in action:
                    home(adb_path)
                    
                elif "Stop" in action:
                    save_steps_json(current_steps, record_dir)
                    time.sleep(1)
                    steps_file = os.path.join(record_dir, "steps.json")

                    append_to_memrag_ndjson(Path(steps_file), instruction, Path(mem_json))
                    print("✅ Memrag_json saved →", mem_json)
                    print("🧠 Rebuilding MEM FAISS index")
                    rag(mem_json, mem_dir, to_doc_fn = _to_mem_documents)
                    print("✔ FAISS index update done.\n")


                    if os.path.exists(steps_file) and os.path.getsize(steps_file) > 0:
                        html_path = generate_html(
                            run_dir = record_dir,
                            model = "Mobile_Agent_4o",
                            run = "",
                            task = task_name
                        )
                        print("✅ HTML saved →", html_path)
                    else:
                        print("❌ steps.json not properly saved, skipping HTML generation")
                    break
                
                time.sleep(5)
                

                last_perception_infos = copy.deepcopy(perception_infos)
                last_screenshot_file = "./rag_screenshot/last_screenshot.jpg"
                last_keyboard = keyboard
                if os.path.exists(last_screenshot_file):
                    os.remove(last_screenshot_file)
                os.rename(screenshot_file, last_screenshot_file)
                
                perception_infos, width, height = get_perception_infos(adb_path, screenshot_file)
                shutil.rmtree(temp_file)
                os.mkdir(temp_file)
                screenshot_record = os.path.join(record_screenshot_dir, f"{step_id:04d}.jpg")
                shutil.copy2(screenshot_file, screenshot_record)
                
                keyboard = False
                result = subprocess.run(f"{adb_path} shell dumpsys input_method | grep -E 'mInputShown'", shell=True, capture_output=True, text=True)
                if "mInputShown=true" in result.stdout:
                    keyboard = True
                else:
                    for perception_info in perception_infos:
                        if perception_info['coordinates'][1] < keyboard_height_limit:
                            continue
                        if 'ADB Keyboard' in perception_info['text']:
                            keyboard = True
                            break
                
               
                if reflection_switch:
                    prompt_reflect = get_reflect_prompt(
                        instruction, 
                        last_perception_infos, 
                        perception_infos, 
                        width, height, 
                        last_keyboard, 
                        keyboard, 
                        summary, 
                        action, 
                        add_info
                    )
                    chat_reflect = init_reflect_chat()
                    chat_reflect = add_response_two_image("user", prompt_reflect, chat_reflect, [last_screenshot_file, screenshot_file])
                    complete_task = ""  
                    output_reflect = inference_chat(chat_reflect, 'gpt-4o', API_url, token)
                    match = re.search(r"### Answer ###\s*([ABC])\b", output_reflect)
                    reflect  = match.group(1) if match else ""
                    if "A" in reflect :
                        thought_history.append(thought)
                        summary_history.append(summary)
                        action_history.append(action)

                        if output_reflect:
                            complete_task_content = ""
                            insight_content = ""
                            if "### COMPLETE_TASK ###" in output_reflect:
                                complete_task_content = output_reflect.split("### COMPLETE_TASK ###")[-1].split("### INSIGHT ###")[0].strip()
                            if "### INSIGHT ###" in output_reflect:
                                insight_content = output_reflect.split("### INSIGHT ###")[-1].split("###")[0].strip()
                            
                            if complete_task_content and complete_task_content != "None":
                                memory += complete_task_content + "\n"
                                record_task = complete_task_content + "\n"
                            if insight_content and insight_content != "None":
                                memory += insight_content + "\n"
                                record_task = insight_content + "\n"
                                complete_task += record_task

                        prompt_planning = get_process_prompt(
                            instruction, 
                            thought_history, 
                            summary_history, 
                            action_history, 
                            memory, 
                            add_info,
                            complete_task,
                            record_task
                        )
                        chat_planning = init_memory_chat()
                        chat_planning = add_response("user", prompt_planning, chat_planning)
                        output_planning = inference_chat(chat_planning, 'gpt-4.1', API_url, token)
                        chat_planning = add_response("assistant", output_planning, chat_planning)
                        status = "#" * 50 + " Processing " + "#" * 50
                        print(status)
                        print(output_planning)
                        print('#' * len(status))


                        current_task = ""
                        decision = ""
                        reason = ""
                        

                        if "CURRENT_TASK:" in output_planning:
                            current_task = output_planning.split("CURRENT_TASK:")[1].split("\n")[0].strip()
                        
                        

                        if "DECISION:" in output_planning:
                            decision = output_planning.split("DECISION:")[1].split("\n")[0].strip()
                        

                        if "REASON:" in output_planning:
                            reason = output_planning.split("REASON:")[1].split("\n")[0].strip()
                        
                        print(f"Current Task: {current_task}")
                        print(f"Complete Task: {complete_task}")
                        print(f"Decision: {decision}")
                        print(f"Reason: {reason}")
                        
                        
                        if "SWITCH_TO_PLANNING" in decision:
                            mode = "planning"
                            print("Switching back to planning mode...")
                        elif "CONTINUE_CURRENT_APP" in decision:
                            print("Continuing with current app...")
                        else:
                            print(f"Unknown decision: {decision}, continuing with current app...")
                    
                    elif "B" in reflect :  
                        error_flag = True
                        back(adb_path)
                        
                    elif "C" in reflect :  
                        error_flag = True
                        # mode = "planning" 
                
                else:
                    thought_history.append(thought)
                    summary_history.append(summary)
                    action_history.append(action)
                    

                    prompt_planning = get_process_prompt(
                        instruction, 
                        thought_history, 
                        summary_history, 
                        action_history, 
                        memory, 
                        add_info,
                        complete_task,
                        record_task
                    )
                    chat_planning = init_memory_chat()
                    chat_planning = add_response("user", prompt_planning, chat_planning)
                    output_planning = inference_chat(chat_planning, 'gpt-4.1', API_url, token)
                    chat_planning = add_response("assistant", output_planning, chat_planning)
                    status = "#" * 50 + " Processing " + "#" * 50
                    print(status)
                    print(output_planning)
                    print('#' * len(status))
                    

                    current_task = ""
                    decision = ""
                    reason = ""
                    

                    if "CURRENT_TASK:" in output_planning:
                        current_task = output_planning.split("CURRENT_TASK:")[1].split("\n")[0].strip()
                    
                    if "DECISION:" in output_planning:
                        decision = output_planning.split("DECISION:")[1].split("\n")[0].strip()
                    
                    if "REASON:" in output_planning:
                        reason = output_planning.split("REASON:")[1].split("\n")[0].strip()
                    
                    print(f"Current Task: {current_task}")
                    print(f"Complete Task: {complete_task}")
                    print(f"Decision: {decision}")
                    print(f"Reason: {reason}")
                    
                    if "SWITCH_TO_PLANNING" in decision:
                        mode = "planning"
                        print("Switching back to planning mode...")


                if reflection_switch:
                    current_steps[-1]["reflection"] = reflect
                    if 'A' in reflect:
                        current_steps[-1]["planning"] = output_planning
                else:
                    current_steps[-1]["planning"] = output_planning
                    
                existing_pkgs, max_id = handle_new_installs(
            existing_pkgs,
            max_id,
            adb_path,      
            json_dir,          
            index_dir              
        )

            os.remove(last_screenshot_file)

if __name__ == "__main__":
    main()




