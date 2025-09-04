import os
import time
import subprocess
from PIL import Image



def get_screenshot(adb_path):
    command = adb_path + " shell rm /sdcard/screenshot.png"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    time.sleep(0.5)
    command = adb_path + " shell screencap -p /sdcard/screenshot.png"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    time.sleep(0.5)
    command = adb_path + " pull /sdcard/screenshot.png ./rag_screenshot"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    time.sleep(0.5)
    image_path = "./rag_screenshot/screenshot.png"
    save_path = "./rag_screenshot/screenshot.jpg"
    image = Image.open(image_path)
    image.convert("RGB").save(save_path, "JPEG")
    time.sleep(0.5)
    os.remove(image_path)



def tap(adb_path, x, y):
    command = adb_path + f" shell input tap {x} {y}"
    subprocess.run(command, capture_output=True, text=True, shell=True)


def type(adb_path, text):
    text = text.replace("\\n", "_").replace("\n", "_")
    for char in text:
        if char == ' ':
            command = adb_path + f" shell input text %s"
            subprocess.run(command, capture_output=True, text=True, shell=True)
        elif char == '_':
            command = adb_path + f" shell input keyevent 66"
            subprocess.run(command, capture_output=True, text=True, shell=True)
        elif 'a' <= char <= 'z' or 'A' <= char <= 'Z' or char.isdigit():
            command = adb_path + f" shell input text {char}"
            subprocess.run(command, capture_output=True, text=True, shell=True)
        elif char in '-.,!?@\'°/:;()':
            command = adb_path + f" shell input text \"{char}\""
            subprocess.run(command, capture_output=True, text=True, shell=True)
        else:
            command = adb_path + f" shell am broadcast -a ADB_INPUT_TEXT --es msg \"{char}\""
            subprocess.run(command, capture_output=True, text=True, shell=True)




def slide(adb_path, x1, y1, x2, y2):
    command = adb_path + f" shell input swipe {x1} {y1} {x2} {y2} 500"
    subprocess.run(command, capture_output=True, text=True, shell=True)

def slide_left(adb_path):    # slide to left
    command = adb_path + f" shell input swipe 200 1200 900 1200 300"
    subprocess.run(command, capture_output=True, text=True, shell=True)

def slide_right(adb_path):    # slide to right
    command = adb_path + f" shell input swipe 900 1200 200 1200 300"
    subprocess.run(command, capture_output=True, text=True, shell=True)

def slide_down(adb_path):    # slide to down
    command = adb_path + f" shell input swipe 540 1800 540 800 300"   
    subprocess.run(command, capture_output=True, text=True, shell=True)

def slide_up(adb_path):    # slide to up
    command = adb_path + f" shell input swipe 540 800 540 1800 300"
    subprocess.run(command, capture_output=True, text=True, shell=True)

def back(adb_path):
    command = adb_path + f" shell input keyevent 4"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    
def home(adb_path):
    command = adb_path + f" shell am start -a android.intent.action.MAIN -c android.intent.category.HOME"
    subprocess.run(command, capture_output=True, text=True, shell=True)
    