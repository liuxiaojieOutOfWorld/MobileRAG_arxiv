import re
import shutil
import os




def get_planning_prompt(instruction, summary_history, action_history, add_info, completed_content, memory, rag_info, current_task="", complete_task="", memrag = ""):
    prompt = "### Task Planning Phase ###\n"
    prompt += f"User's instruction: \"{instruction}\"\n\n"

    if len(action_history) > 0:
        prompt += "### History operations ###\n"
        prompt += "Before this turn, some operations have been executed. You need to refer to the completed operations to decide the next operation. These operations are as follow:\n"
        for i in range(len(action_history)):
            prompt += f"Step-{i+1}: [Operation: " + summary_history[i].split(" to ")[0].strip() + "; Action: " + action_history[i] + "]\n"
        prompt += "\n"

    if rag_info != "":
        prompt += "### RAG Queries Results ###\n"
        prompt += "These are cached results from earlier Local-/Inter-RAG queries. You MUST use this information in your Thought section:\n"
        prompt += "When the user's instruction refers to a general or superlative concept (such as 'the most popular music app', 'the best restaurant nearby', 'the most recommended app', etc.), and you cannot directly determine the exact app or item from the instruction or local data, you should first use InterRAG (internet search or external knowledge) to identify the most suitable candidate. Only after you have determined the specific app or item should you proceed to check its availability locally or take further actions.\n"
        prompt += "If LocalRAG returns relevant result, means the app is installed on the device, use **Open app(app_name)** to open the app.\n"
        prompt += "If LocalRAG returns no relevant result, treat the app as \"not installed\" → immediately choose **Open app (Play Store)** to download it.\n"
        prompt += "If the user's instruction does not specify an exact app name, and you need to determine which app can accomplish the task (such as playing a specific song, opening a type of file, or performing a general function), you MUST first use InterRAG to search for which app(s) are suitable for this task (e.g., which app can play this specific music). Only after you have identified a specific app name should you proceed to check if it is installed (using LocalRAG) or take further actions.\n"
        prompt += "Search Results:\n" + rag_info.strip() + "\n\n"

    if memory != "":
        prompt += "### Memory ###\n"
        prompt += "During the operations, you record the following contents on the screenshot for use in subsequent operations:\n"
        prompt += "Memory:\n" + memory + "\n\n"
    
    if completed_content != "":
        prompt += "### Progress ###\n"
        prompt += "After completing the history operations, you have the following thoughts about the progress of user's instruction completion:\n"
        prompt += "Completed contents:\n" + completed_content + "\n\n"

    if add_info != "":
        prompt += "### Hint ###\n"
        prompt += "There are hints to help you complete the user\'s instructions. The hints are as follow:\n"
        prompt += add_info
        prompt += "\n\n"
    

    if current_task and complete_task:
        prompt += "### Task Status Analysis ###\n"
        prompt += f"Current task to complete: {current_task}\n"
        prompt += f"Already completed: {complete_task}\n\n"
        prompt += "Based on the task completion status, find the next step.\n"

    if memrag != "":
        prompt += "### Historical records for reference only ###\n"
        prompt += (
            "The following memrag contains examples of previously successful instructions and actions. "
            "These are provided for your reference only and are not mandatory. "
            "You are encouraged to use your own judgment and adapt your actions to the current task as needed. "
            "Do not feel obligated to strictly follow the memrag content if it does not fit the present situation.\n"
        )
        prompt += f"memrag: {memrag}\n\n"
        

        prompt += "### MemRAG Reuse Strategy ###\n"
        prompt += "1. **App Selection**: If memrag contains similar tasks with successful app choices, directly use those apps without repeating LocalRAG or InterRAG queries.\n"
        prompt += "2. **Message Content Reuse**: If memrag contains a 'Type' action with a suitable message for a similar recipient, directly reuse that message content, only changing the recipient's name.\n"
        prompt += "3. **Action Sequence**: If memrag shows a successful action sequence for similar tasks, adapt and reuse that sequence.\n"
        prompt += "4. **Content Adaptation**: When reusing content from memrag, only modify what's necessary (e.g., recipient name, specific details) while keeping the core message structure.\n\n"
        
        prompt += "### Examples of Content Reuse ###\n"
        prompt += "- If memrag shows: `Type (Hey Mike, want to watch 'The Boys' Season 4? Here's a quick intro: ...)`\n"
        prompt += "- And current task is to send similar message to Jelly, use: `Type (Hey Jelly, want to watch 'The Boys' Season 4? Here's a quick intro: ...)`\n"
        prompt += "- If memrag shows successful app sequence: `Open app(\"Google Messages\")` → `Tap (445, 2276)` → `Type (...)`\n"
        prompt += "- Reuse the same sequence for similar messaging tasks.\n\n"

    prompt += (
        "**App Selection Logic:**\n"
        "- **Priority 1: MemRAG History**: If memrag contains successful app choices for similar tasks, directly use those apps without LocalRAG or InterRAG queries.\n"
        "- **Priority 2: Direct App Names**: If the user's instruction clearly specifies an exact app name (e.g., 'Spotify', 'Google Maps'), or refers to a common/standard app type (e.g., notepad, notes, calendar, camera, browser, phone, messaging), you should directly use LocalRAG to check for this app and proceed.\n"
        "- **Priority 3: Real-time Information**: If the user's instruction requires real-time or up-to-date information (for example, contains words like 'latest', 'currently', 'real-time', 'now'), you MUST use InterRAG to obtain the most current information.\n"
        "- **Priority 4: Vague Instructions**: Only use InterRAG if the instruction is vague, superlative, or you cannot determine the exact app from the instruction or local data.\n\n"
    )

    prompt += "### Available Actions ###\n"
    prompt += "1. **Query InterRAG (your_query)**"
    prompt += "   - Search for apps that can be implemented\n"
    prompt += "   - When using InterRAG, you MUST always include the specific target from the user's instruction (such as the song name, album name, place, or product) in your query. "
    prompt += "   - For example, if the instruction is \"add the album 'Happier Than Ever' to my library\", the key information should be the 'Happier Than Ever' and 'which app can'"
    prompt += "   - Use ONLY when you cannot determine a specific app to use for the user's instruction\n"
    prompt += "   - Do NOT use InterRAG if you already know which app to open or can find the app using LocalRAG\n"
    prompt += "   - InterRAG is for searching general information or finding which app to use when no app is specified or found\n\n"


    prompt += "2. **Query LocalRAG (your_keyword)**\n"
    prompt += "   - Find installed apps\n"
    prompt += "   - Your_keyword should be the exact app name or a common app type from the instruction, or the result of a previous InterRAG if the app was not clear.\n"
    prompt += "   - Use when you need to find information about installed apps\n"
    prompt += "   - Use when you need to verify if an app is installed\n"
    prompt += "   - Use when you need to get app details and functions\n\n"

    prompt += "3. **Open app \"(app name)\"**"   
    prompt += "   - Launch specific app\n"
    prompt += "   - Use when you know which app to open\n"
    prompt += "   - Use when you need to switch to a new app\n"
    prompt += "   - Use when you need to continue task in another app\n\n"
    
    prompt += "4. Switch to Action Mode - If you have enough information and want to directly start interacting with the current screen, you can choose to switch to action mode.\n\n"
    
    prompt += "### Output Format ###\n"
    prompt += "You MUST output ONLY ONE set of the following format for each response, describing ONLY ONE action. Do NOT output multiple sets, do NOT output any search history, and do NOT output any previous attempts in your response.\n"
    prompt += "You MUST follow this EXACT format. Do not add any other sections:\n\n"
    prompt += "### Thought ###\n"
    prompt += "[Think about the current state and what needs to be done next]\n\n"
    prompt += "### Action ###\n"
    prompt += "[Choose ONE: Query LocalRAG(keyword) / Query InterRAG(query) / Open app(name) / Switch to Action Mode]\n\n"
    prompt += "### Operation ###\n"
    prompt += "[Brief description of the operation]\n"
    

    
    return prompt

def get_action_prompt(instruction, clickable_infos, width, height, keyboard, thought_history, summary_history, action_history, memory, add_info, decision, current_task="", complete_task="", memrag = ""):
    prompt = "### Background ###\n"
    prompt += f"This image is a phone screenshot. Its width is {width} pixels and its height is {height} pixels. The user's instruction is: {instruction}.\n\n"

    prompt += "### Screenshot information ###\n"
    prompt += "In order to help you better perceive the content in this screenshot, we extract some information on the current screenshot through system files. "
    prompt += "This information consists of two parts: coordinates; content. "
    prompt += "The format of the coordinates is [x, y], x is the pixel from left to right and y is the pixel from top to bottom; the content is a text or an icon description respectively. "
    prompt += "The information is as follow:\n"

    prompt += "You MUST use only the information listed above (coordinates and content) to make your decision. Do NOT assume you can open or view the image in any other way.\n"
    
    for clickable_info in clickable_infos:
        if clickable_info['text'] != "" and clickable_info['text'] != "icon: None" and clickable_info['coordinates'] != (0, 0):
            prompt += f"{clickable_info['coordinates']}; {clickable_info['text']}\n"
    
    prompt += "Please note that this information is not necessarily accurate. You need to combine the screenshot to understand."
    prompt += "\n\n"

 
    prompt += "### Keyboard status ###\n"
    prompt += "We extract the keyboard status of the current screenshot and it is whether the keyboard of the current screenshot is activated.\n"
    prompt += "The keyboard status is as follow:\n"
    if keyboard:
        prompt += "The keyboard has been activated and you can type."
    else:
        prompt += "The keyboard has not been activated and you can't type."
    prompt += "\n\n"

    if memrag != "":
        prompt += "### Historical records for reference only ###\n"
        prompt += (
            "The following memrag contains examples of previously successful instructions and actions. "
            "These are provided for your reference only and are not mandatory. "
            "You are encouraged to use your own judgment and adapt your actions to the current task as needed. "
            "Do not feel obligated to strictly follow the memrag content if it does not fit the present situation.\n"
        )
        prompt += f"memrag: {memrag}\n\n"
        

        prompt += "### MemRAG Reuse Strategy ###\n"
        prompt += "1. **App Selection**: If memrag contains similar tasks with successful app choices, directly use those apps without repeating LocalRAG or InterRAG queries.\n"
        prompt += "2. **Message Content Reuse**: If memrag contains a 'Type' action with a suitable message for a similar recipient, directly reuse that message content, only changing the recipient's name.\n"
        prompt += "3. **Action Sequence**: If memrag shows a successful action sequence for similar tasks, adapt and reuse that sequence.\n"
        prompt += "4. **Content Adaptation**: When reusing content from memrag, only modify what's necessary (e.g., recipient name, specific details) while keeping the core message structure.\n\n"
        
        prompt += "### Examples of Content Reuse ###\n"
        prompt += "- If memrag shows: `Type (Hey Mike, want to watch 'The Boys' Season 4? Here's a quick intro: ...)`\n"
        prompt += "- And current task is to send similar message to Jelly, use: `Type (Hey Jelly, want to watch 'The Boys' Season 4? Here's a quick intro: ...)`\n"
        prompt += "- If memrag shows successful app sequence: `Open app(\"Google Messages\")` → `Tap (445, 2276)` → `Type (...)`\n"
        prompt += "- Reuse the same sequence for similar messaging tasks.\n\n"
        
    if len(thought_history) > 1:
        prompt += "\n### History operations ###\n"
        for i in range(len(summary_history)):
            operation = summary_history[i].split(" to ")[0].strip()
            prompt += f"Step-{i+1}: [Operation thought: {operation}; Operation action: {action_history[i]}]\n"
        
        prompt += "\n### Progress thinking ###\n"
        prompt += "Completed contents:\n" + memory + "\n\n"
        

        if current_task and complete_task:
            prompt += "\n### Task Completion Status ###\n"
            prompt += f"Current task to complete: {current_task}\n"
            prompt += f"Already completed: {complete_task}\n\n"
        
        prompt += "\n### Current operation ###\n"
        prompt += f"Operation thought: {thought_history[-1]}\n"
        operation = summary_history[-1].split(" to ")[0].strip()
        prompt += f"Operation action: {action_history[len(summary_history)-1]}; Meets your expectation: {complete_task}\n"
        
        prompt += "\n### Additional Information ###\n"
        prompt += add_info + "\n\n"
        
        prompt += "### Response requirements ###\n"
        prompt += "When you need to find something on the page (such as an app, place, product, etc.), if there is a search bar or search button on the page, you should prioritize clicking the search bar and entering the relevant keyword to search. This is usually the fastest and most direct way to locate your target.\n"
        prompt += "Now you need to combine all of the above to perform just one action on the current page. You must choose one of the following six actions. Please output the action in the required format:\n"
        prompt += "1. **Tap (x, y)**: Tap the position (x, y) in current page.\n"
        prompt += "   · Format: Tap (100, 200)\n"
        prompt += "   · For example: Tap (100, 200), Tap (500, 300), etc.\n"
        prompt += "   · You must specify the exact coordinates to tap on.\n"
        prompt += "   · For example, when review at position (500,300), Tap (500, 300)\n"
        prompt += "   · Do not use tap to open app.\n"
        
        prompt += "2. **Swipe (x1, y1), (x2, y2)**: Swipe from position (x1, y1) to position (x2, y2).\n"
        prompt += "   · Format: Swipe (x1, y1), (x2, y2)\n"
        prompt += "   · For example: Swipe (100, 200), (300, 400)\n"
        prompt += "   · You must specify the start and end coordinates.\n"
        prompt += "   · If you want to swipe down the page, use: Swipe (500, 1800), (500, 1400)\n"
        if keyboard:
            prompt += "3. **Type (text)**: Type the \"text\" in the input box.\n"
            prompt += "   · Format: Type (text)\n"
            prompt += "   · For example: Type (restaurant), Type (Hello world), etc.\n"
            prompt += "   · You must specify what text to type.\n"
        else:
            prompt += "Unable to Type. You cannot use the action \"Type\" because the keyboard has not been activated. If you want to type, please first activate the keyboard by tapping on the input box on the screen.\n"
        
        prompt += "4. **Back**: Go back to the previous page.\n"
        prompt += "   · Format: Back\n"
        prompt += "   · No additional parameters needed.\n"
        
        prompt += "5. **Home**: Return to the home screen.\n"
        prompt += "   · Format: Home\n"
        prompt += "   · No additional parameters needed.\n"
        

        prompt += "6. **Stop**: Use when all user instructions are fully satisfied.\n"
        prompt += "Before choosing Stop, you MUST review the user's instruction and confirm that every required step (including collecting, recording, saving, or reporting information) has been fully completed. Do not choose Stop if any part of the instruction is still pending.\n"
        prompt += "You are ONLY allowed to choose Stop if the variable {decision} is STOP. If {decision} is not STOP, you MUST NOT choose Stop.\n"

        prompt += "\n### Output Format ###\n"
        prompt += "You MUST output ONLY ONE set of the following format for each response, describing ONLY ONE action. Do NOT output multiple sets, do NOT output any search history, and do NOT output any previous attempts in your response.\n"
        prompt += "Do NOT include any previous search queries, app names, or actions from earlier steps in your output. Only output the current step's Thought, Action, and Operation.\n"
        prompt += "You MUST follow this EXACT format. Do not add any other sections:\n\n"
        prompt += "### Thought ###\n"
        prompt += "[Think about the current state and what needs to be done next]\n\n"
        prompt += "### Action ###\n"
        prompt += "[Choose ONE: Tap (x, y) / Swipe (x1, y1), (x2, y2) / Type (text) / Back / Home / Stop]\n\n"
        prompt += "### Operation ###\n"
        prompt += "[Brief description of the operation]\n"
    else:
        prompt += "\n### Current operation ###\n"
        prompt += f"Operation thought: {thought_history[-1]}\n"
        operation = summary_history[-1].split(" to ")[0].strip()
        prompt += f"Operation action: {action_history[len(summary_history)-1]}; Meets your expectation: {complete_task}\n"
        
        prompt += "\n### Additional Information ###\n"
        prompt += add_info + "\n\n"
        
        prompt += "### Response requirements ###\n"
        prompt += "When you need to find something on the page (such as an app, place, product, etc.), if there is a search bar or search button on the page, you should prioritize clicking the search bar and entering the relevant keyword to search. This is usually the fastest and most direct way to locate your target.\n"
        prompt += "Now you need to combine all of the above to perform just one action on the current page. You must choose one of the following six actions. Please output the action in the required format:\n"
        prompt += "1. **Tap (x, y)**: Tap the position (x, y) in current page.\n"
        prompt += "   · Format: Tap (100, 200)\n"
        prompt += "   · For example: Tap (100, 200), Tap (500, 300), etc.\n"
        prompt += "   · You must specify the exact coordinates to tap on.\n"
        
        prompt += "2. **Swipe (x1, y1), (x2, y2)**: Swipe from position (x1, y1) to position (x2, y2).\n"
        prompt += "   · Format: Swipe (x1, y1), (x2, y2)\n"
        prompt += "   · For example: Swipe (100, 200), (300, 400)\n"
        prompt += "   · You must specify the start and end coordinates.\n"
        # prompt += "   · You can use it when need more information in this page.\n"
        prompt += "   · If you want to swipe down the page, use: Swipe (500, 1800), (500, 1400)\n"
        if keyboard:
            prompt += "3. **Type (text)**: Type the \"text\" in the input box.\n"
            prompt += "   · Format: Type (text)\n"
            prompt += "   · For example: Type (restaurant), Type (Hello world), etc.\n"
            prompt += "   · You must specify what text to type.\n"
        else:
            prompt += "Unable to Type. You cannot use the action \"Type\" because the keyboard has not been activated. If you want to type, please first activate the keyboard by tapping on the input box on the screen.\n"
        
        prompt += "4. **Back**: Go back to the previous page.\n"
        prompt += "   · Format: Back\n"
        prompt += "   · No additional parameters needed.\n"
        
        prompt += "5. **Home**: Return to the home screen.\n"
        prompt += "   · Format: Home\n"
        prompt += "   · No additional parameters needed.\n"
        
        prompt += "6. **Stop**: Use when all user instructions are fully satisfied.\n"
        # prompt += f"You MUST only choose Stop if you are absolutely certain that ALL requirements in the user's instruction (\"{instruction}\") have been fully completed and satisfied. Do not choose Stop if there is any unfinished step or if you are unsure. The Stop action must correspond exactly to the user's instruction and only be used when the task is truly complete.\n"
        prompt += "Before choosing Stop, you MUST review the user's instruction (\"{instruction}\") and confirm that every required step (including collecting, recording, saving, or reporting information) has been fully completed. Do not choose Stop if any part of the instruction is still pending.\n"
        prompt += "You are ONLY allowed to choose Stop if the variable {decision} is STOP. If {decision} is not STOP, you MUST NOT choose Stop.\n"

        # prompt += f"   · If the variable {decision} is STOP, you MUST choose Stop as your action. Do NOT choose any other action. Do NOT perform Back, Home, Tap, Swipe, or Type. You must stop immediately.\n"
     
        prompt += "\n### Output Format ###\n"
        prompt += "You MUST output ONLY ONE set of the following format for each response, describing ONLY ONE action. Do NOT output multiple sets, do NOT output any search history, and do NOT output any previous attempts in your response.\n"
        # prompt += f"If {decision} is STOP, your ONLY valid output for Action is Stop. Any other action will be rejected.\n"
        prompt += "Do NOT include any previous search queries, app names, or actions from earlier steps in your output. Only output the current step's Thought, Action, and Operation.\n"
        prompt += "You MUST follow this EXACT format. Do not add any other sections:\n\n"
        prompt += "### Thought ###\n"
        prompt += "[Think about the current state and what needs to be done next]\n\n"
        prompt += "### Action ###\n"
        prompt += "[Choose ONE: Tap (x, y) / Swipe (x1, y1), (x2, y2) / Type (text) / Back / Home / Stop]\n\n"
        prompt += "### Operation ###\n"
        prompt += "[Brief description of the operation]\n"  

    return prompt


def get_reflect_prompt(instruction, clickable_infos1, clickable_infos2, width, height, keyboard1, keyboard2, summary, action, add_info, memory="", opened_memory="", complete_app_content=None):
    prompt = "### Background ###\n"
    prompt += f"This image is a phone screenshot. Its width is {width} pixels and its height is {height} pixels. The user's instruction is: {instruction}.\n\n"

    if complete_app_content:
        prompt += "### Completed App Content ###\n"
        prompt += "The following content has been completed in previous apps:\n"
        for app, content in complete_app_content.items():
            prompt += f"App: {app}\n"
            prompt += f"Completed Content:\n{content}\n\n"
        prompt += "IMPORTANT: Use this information to avoid reopening apps unnecessarily. If you need information that's already been collected, refer to this section.\n\n"

    prompt += "### Operation Summary ###\n"
    prompt += f"Previous operation summary: {summary}\n"
    prompt += f"Previous action: {action}\n\n"

    if memory:
        prompt += "### Memory (Progress) ###\n"
        prompt += f"Current memory/progress: {memory}\n\n"

    prompt += "### Additional Information ###\n"
    prompt += f"{add_info}\n\n"

    prompt += "### Reflection Task ###\n"
    prompt += (
        "You must reflect on the result of the last operation and answer the following:\n"
        "1. Did the last operation successfully complete the current subtask?\n"
        "2. What new key information or progress did you obtain?\n"
        "3. What should be recorded in memory for subsequent planning and process?\n"
    )
    prompt += "You MUST output in the following strict format (do NOT omit any section):\n"
    prompt += "### Answer ###\n[A/B/C] (A: Success, B: Failure, C: Needs replan)\n\n"
    prompt += (" Whether the result of the \"Operation action\" meets your expectation of \"Operation thought\"?\n"
               " A: The result of the \"Operation action\" meets my expectation of \"Operation thought\".\n"
               " B: The \"Operation action\" results in a wrong page and I need to return to the previous page.\n"
               " C: The \"Operation action\" produces no changes.")
    prompt += "### COMPLETE_TASK ###\n"
    prompt += ("You MUST explicitly list every key information or result you obtained in this operation, one by one, in a way that can be directly copied to memory. "
                "You MUST refer to the user's instruction and enumerate all required items. Do NOT just say 'completed' or 'done'. "
                "If you fail to do so, you will be penalized.\n")
    prompt += "[Summarize all new key information or completed content from this operation, in a way that can be directly written to memory/record_task. If nothing new, write 'None.']\n\n"
    prompt += "### INSIGHT ###\n[Summarize any additional insights, progress, or context that should be recorded for future planning. If nothing, write 'None.'] You can consider {instruction} to decide the record information.\n\n"
    prompt += "If you do NOT output in this exact format, the process will fail and you will be penalized.\n"
    prompt += "For example：\n### Answer ###\nA\n\n### COMPLETE_TASK ###\n1. Collected director: Guo Hu. 2. Collected rating: 9.7.\n\n### INSIGHT ###\nThe series details for 'A Dream Within A Dream' have been collected and can be sent to Jellya.\n"
    return prompt


def get_memory_prompt(insight, complete_app_content=None):
    prompt = ""  
    
    if insight != "":
        prompt += "### Important content ###\n"
        prompt += insight
        prompt += "\n\n"
    
    if complete_app_content:
        prompt += "### Completed App Content ###\n"
        prompt += "The following content has been completed in previous apps:\n"
        for app, content in complete_app_content.items():
            prompt += f"App: {app}\n"
            prompt += f"Completed Content:\n{content}\n\n"
        prompt += "IMPORTANT: Use this information to avoid reopening apps unnecessarily. If you need information that's already been collected, refer to the completed content above instead of reopening the app.\n\n"
    
    
    prompt += "### Response requirements ###\n"
    prompt += "Please analyze the following:\n"
    prompt += "1. If there is any useful information that should be remembered for future operations\n\n"
    prompt += "If there is relevant content, please output it. If not, please output \"None\".\n\n"
    
    prompt += "### Output format ###\n"
    prompt += "Your output format is:\n"
    prompt += "### Important content ###\n"
    prompt += "1. Useful information to remember\n"
    prompt += "If nothing is relevant, output \"None\".\n"
    prompt += "Please do not repeatedly output the information in ### Memory ###."
    
    return prompt

def get_process_prompt(instruction, thought_history, summary_history, action_history, memory, add_info, complete_task, record_task):
    prompt = "### Background ###\n"
    prompt += f"There is an user's instruction which is: {instruction}. You are a mobile phone operating assistant and are operating the user's mobile phone.\n\n"
    
    if len(thought_history) > 1:
        prompt += "\n### History operations ###\n"
        for i in range(len(summary_history)):
            operation = summary_history[i].split(" to ")[0].strip()
            prompt += f"Step-{i+1}: [Operation thought: {operation}; Operation action: {action_history[i]}]\n"
        prompt += f"Operation action: {action_history[len(summary_history)-1]}; Meets your expectation: {complete_task}\n"

        prompt += "\n### Task Analysis ###\n"
        prompt += "Please analyze the user's instruction and current progress:\n"
        prompt += f"User's instruction: \"{instruction}\"\n"
        prompt += f"Previously recorded completion process: {memory}\n\n"
        prompt += f"Latest action result: {complete_task}\n"
        prompt += f"Latest action completed successfully: {action_history[-1]}\n"

        prompt += "### Key Information from Current Page (record_task) ###\n"
        prompt += "The following is the key information extracted from the current page (record_task). You do NOT need to copy or save it again—just use it directly for your reasoning and planning.\n"
        prompt += f"{record_task}\n\n"

        prompt += "### Task Breakdown ###\n"
        prompt += "Break down the user's instruction into specific tasks:\n"
        prompt += "1. What information needs to be found/collected?\n"
        prompt += "2. Which apps need to be used?\n"
        prompt += "3. What actions need to be performed in each app?\n"
        prompt += "4. What information needs to be recorded/saved?\n\n"
        
        prompt += "### Progress Verification ###\n"
        prompt += "Compare the instruction requirements with current progress:\n"
        prompt += "1. What has been completed?\n"
        prompt += "2. What is still pending?\n"
        prompt += "3. Are we ready to move to the next app/task?\n\n"
        
        prompt += "### Decision Making ###\n"
        prompt += "Based on the analysis above, decide:\n"
        prompt += "1. If all app tasks are completed and the user's instruction is fully satisfied, Choose: STOP\n"
        prompt += "2. If current app/task is complete (but there are still additional steps required to fully satisfy the user's instruction) and ready to switch to planning mode, Choose: SWITCH_TO_PLANNING\n"
        prompt += "3. If more work is needed in current app/task, Choose: CONTINUE_CURRENT_APP\n\n"
        
        prompt += "### Response Format ###\n"
        prompt += "You must respond in the following format:\n"
        prompt += "CURRENT_TASK: [Detailed description of the specific task that needs to be completed]\n"
        prompt += "DECISION: [Choose: CONTINUE_CURRENT_APP | SWITCH_TO_PLANNING | STOP]\n"
        prompt += "REASON: [Explain the reason for the decision]\n\n"
        
        prompt += "### Decision Guidelines ###\n"
        prompt += "- CONTINUE_CURRENT_APP: Current app task is not yet completed, need to continue operating in the current app\n"
        prompt += "- SWITCH_TO_PLANNING: Current app task is completed, need to switch back to planning mode to decide the next app\n"
        prompt += "- STOP: All app tasks are completed and the user's instruction is fully satisfied, end the process.\n"
        
        prompt += "\n### STOP Decision Priority ###\n"
        prompt += "IMPORTANT: You should ONLY choose STOP decision when ALL of the following conditions are met:\n"
        prompt += "1. All required information has been found and collected\n"
        prompt += "2. All necessary actions have been completed in all required apps\n"
        prompt += "3. The user's instruction has been fully satisfied\n"
        prompt += "4. No further actions are needed to complete the task\n"
        prompt += "5. The current action has successfully completed a key part of the task\n\n"
        prompt += "CRITICAL: Do NOT choose STOP if:\n"
        prompt += "- You have not yet found the required information\n"
        prompt += "- You have not yet created or saved the required content\n"
        prompt += "- You have not yet completed all steps mentioned in the user's instruction\n"
        prompt += "- You are still in the middle of a multi-step process\n"
        prompt += "- You have only opened an app but not yet performed the required actions\n\n"
        prompt += "Do NOT choose SWITCH_TO_PLANNING if the task is already complete. Choose STOP immediately when all requirements are met.\n"
        prompt += "Avoid unnecessary planning cycles when the task is finished.\n\n"
        
        prompt += "### Task Completion Checklist ###\n"
        prompt += "Before choosing STOP, verify ALL of the following:\n"
        prompt += "✓ All required information has been found and collected\n"
        prompt += "✓ All necessary apps have been used and their tasks completed\n"
        prompt += "✓ All required actions have been performed successfully\n"
        prompt += "✓ All information has been properly recorded/saved\n"
        prompt += "✓ The user's instruction is fully satisfied\n"
        prompt += "✓ No further steps are needed to complete the task\n"
        prompt += "✓ You have not just opened an app but actually completed the required work\n"
        prompt += "✓ You have not just started a process but actually finished it\n\n"
        prompt += "If ANY of the above items are NOT checked, do NOT choose STOP. Continue with the current task or switch to planning mode.\n\n"
        
        prompt += "\n### Additional Information ###\n"
        prompt += add_info + "\n\n"
        
        prompt += "### Response requirements ###\n"
        prompt += "Now you need to analyze the current situation and make a decision. You must respond in the exact format specified above.\n"
        

        prompt += "\n### CRITICAL INSTRUCTION FOR MODE SWITCHING ###\n"
        prompt += "You should only choose SWITCH_TO_PLANNING when all required actions in the current app are fully completed. "
        prompt += "If there are still actions to be performed in the current app (for example, you have found the movie but have not yet added it to the watchlist), you MUST choose CONTINUE_CURRENT_APP. "
        prompt += "As soon as you have completed all required actions in the current app, you MUST immediately choose SWITCH_TO_PLANNING to decide the next steps. "
        prompt += "Do NOT stay in the current app for extra or unnecessary steps after its main tasks are finished.\n\n"
        
    else:
        prompt += "\n### Response requirements ###\n"
        prompt += "This is the first step. You need to start with planning mode.\n"
        prompt += "CURRENT_TASK: [Detailed description of the specific task that needs to be completed]\n"
        prompt += "DECISION: SWITCH_TO_PLANNING\n"
        prompt += "REASON: [Explain the reason for the decision]\n"
    
    return prompt


