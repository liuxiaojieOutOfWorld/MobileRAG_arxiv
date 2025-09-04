import os
from pathlib import Path


ROOT_DIR = Path(__file__).parent.absolute()

# ADB 
ADB_PATH = ""

# API 
API_URL = ""
API_TOKEN = ""
QWEN_API = ""


# model
CAPTION_CALL_METHOD = "api"  # "api" / "local"
CAPTION_MODEL = "qwen-vl-plus"  # "qwen-vl-plus" / "qwen-vl-max" / "qwen-vl-chat" / "qwen-vl-chat-int4"

# Google Search API 
GOOGLE_KEY = ""
GOOGLE_CX = ""

# RAG path
INDEX_DIR = ROOT_DIR / "localRAG"
LOCALRAG_DATA_FILE = INDEX_DIR / "localrag_data.jsonl"

# screenshop record
SCREENSHOT_DIR = ROOT_DIR / "rag_screenshot"

RECORD_DIR = ROOT_DIR / "rag_records"
RECORD_SCREENSHOT_DIR = RECORD_DIR / "screenshots"
TEMP_DIR = ROOT_DIR / "temp"

# NEW ADDED
MEM_JSON = ROOT_DIR / "memRAG" / "memrag_data.jsonl"
MEM_DIR = ROOT_DIR / "memRAG" 

# choose
REFLECTION_SWITCH = True
MEMORY_SWITCH = True

# prompt
ADD_INFO = """
REMINDER: Only output one set of Thought, Action, and Operation. If you output more than one, your answer will be rejected.


IMPORTANT: When **no specific app** is mentioned in the instruction:
1. Use interRAG results decide whether to open an app or not
2. Then follow the app opening process above

For example:
1. Query InterRAG("where can I watch Squid Game")
2. Based on results, use LocalRAG and Open app as needed


IMPORTANT: When opening an app, you MUST:
1. First use "Query LocalRAG" to find if the app is installed on the device
2. Then use "Open app" with the app name to open it 

For example:
1. Query LocalRAG("YouTube") to check if the app is on the device
2. Open app(YouTube) to launch it 

"IMPORTANT:\n"
"- If the user's instruction clearly specifies an exact app name (e.g., \"Open Spotify\", \"Use Google Maps\"), you should directly use LocalRAG to check if the app is installed, and then open it.\n"
"- If the user's instruction does NOT specify an exact app name (e.g., \"play the album 'Happier Than Ever'\", \"find the best restaurant nearby\"), you MUST first use InterRAG to determine which app(s) are suitable for this task. Only after you have identified a specific app name should you proceed to check if it is installed (using LocalRAG) or take further actions.\n\n"

"""

ADD_INFO_PLAN = """
 prompt += "### Task Priority and Logic Flow ###\n"
    prompt += "When planning actions, consider:\n"
    prompt += "1. **MemRAG Learning Priority**:\n"
    prompt += "   - Check memrag first for similar tasks and successful patterns\n"
    prompt += "   - Extract app choices, action sequences, and content from memrag\n"
    prompt += "   - Reuse successful app combinations and action flows when applicable\n"
    prompt += "   - Adapt message content, keeping structure but changing specific details\n"
    prompt += "   - Learn from previous successful task completions\n\n"
    
    prompt += "2. Task Dependencies:\n"
    prompt += "   - Which information needs to be gathered first\n"
    prompt += "   - Which app's output is required for the next step\n"
    prompt += "   - Logical sequence of operations\n\n"
    
    prompt += "3. Information Gathering Priority:\n"
    prompt += "   - Primary information sources (e.g., maps for location, browser for facts)\n"
    prompt += "   - Secondary information processing (e.g., notes, messages)\n"
    prompt += "   - Final output or sharing apps\n\n"
    
    prompt += "4. Action Sequence Rules:\n"
    prompt += "   - Always gather required information before processing it\n"
    prompt += "   - Open information-gathering apps before information-processing apps\n"
    prompt += "   - Follow successful patterns from memrag when available\n"
    
    prompt += "### Balanced Learning Strategy ###\n"
    prompt += "1. **MemRAG for Similar Tasks**:\n"
    prompt += "   - Use memrag when tasks are very similar to previous successful ones\n"
    prompt += "   - Reuse app sequences and content patterns that worked before\n"
    prompt += "   - Adapt existing content rather than creating from scratch\n\n"
    
    prompt += "2. **LocalRAG for App Discovery**:\n"
    prompt += "   - Essential for finding installed apps on the device\n"
    prompt += "   - Use when memrag doesn't contain suitable app choices\n"
    prompt += "   - Critical for verifying app availability and functions\n\n"
    
    prompt += "3. **InterRAG for New Information**:\n"
    prompt += "   - Vital for real-time and up-to-date information\n"
    prompt += "   - Use when memrag doesn't contain current information\n"
    prompt += "   - Essential for finding new apps, products, or services\n\n"
    
    prompt += "4. **Hybrid Approach**:\n"
    prompt += "   - Combine memrag patterns with LocalRAG/InterRAG for new information\n"
    prompt += "   - Use memrag for app choices, LocalRAG for verification, InterRAG for updates\n"
    prompt += "   - Balance efficiency (memrag) with accuracy (RAG queries)\n\n"
    
    prompt += "### Available Actions ###\n"
    prompt += "1. Query LocalRAG (your_keyword)\n"
    prompt += "   - Use when you need to:\n"
    prompt += "     • Find information about installed apps\n"
    prompt += "     • Verify if an app is installed\n"
    prompt += "     • Get app details and functions\n"
    prompt += "     • Search for apps by function (e.g., 'music', 'social', 'productivity')\n"
    prompt += "     • **Use when memrag doesn't have suitable app choices or for verification**\n\n"
    
    prompt += "2. Query InterRAG (your_query)\n"
    prompt += "   - Use when you need to:\n"
    prompt += "     • Get real-time information\n"
    prompt += "     • Search for facts not in LocalRAG\n"
    prompt += "     • Find app alternatives or recommendations\n"
    prompt += "     • Get platform-specific information\n"
    prompt += "     • **Use when memrag doesn't contain current information**\n\n"

    prompt += "3. Open app (exact_app_name)\n"
    prompt += "   - Use when you need to:\n"
    prompt += "     • Launch a specific application\n"
    prompt += "     • Switch to a new app\n"
    prompt += "     • Continue task in another app\n"
    prompt += "     • **Prefer apps from memrag when available, otherwise use verified apps**\n"

       

    """

# make sure file
for dir_path in [SCREENSHOT_DIR, RECORD_DIR, RECORD_SCREENSHOT_DIR, TEMP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True) 
