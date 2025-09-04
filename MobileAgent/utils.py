import json
import os
from datetime import datetime
from MobileAgent.api import inference_chat
import re

def get_gpt_response(prompt, model='gpt-4-turbo', api_url=None, token=None):
    response = inference_chat(prompt, model, api_url, token)
    return response

def parse_action(response):
    try:
        action_match = re.search(r"Action: (.*?)(?:\n|$)", response)
        if action_match:
            return action_match.group(1).strip()
        return None
    except Exception as e:
        print(f"Error parsing action: {str(e)}")
        return None

def save_steps_to_file(steps):
    try:
        os.makedirs("output", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output/steps_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(steps, f, ensure_ascii=False, indent=2)
            
        print(f"Steps saved to {filename}")
    except Exception as e:
        print(f"Error saving steps: {str(e)}") 