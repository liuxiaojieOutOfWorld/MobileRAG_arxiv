from pathlib import Path
import base64, json, mimetypes, argparse, os
from natsort import natsorted
from template import template   
import time
from config import RECORD_SCREENSHOT_DIR 

# ---------- helpers ----------
def img_to_b64(p):
    p = Path(p)                      
    if not p.exists():
        return None

    mime = mimetypes.guess_type(p)[0] or "image/jpeg"
    data = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{data}"

def steps_to_examples(run_dir: Path) -> list[dict]:
    """Convert new-schema steps.json → template examples list"""
    steps = json.loads((run_dir / "steps.json").read_text(encoding="utf-8"))
    shots = RECORD_SCREENSHOT_DIR  

    examples = []
    for st in steps:
        task_text   = st.get("thought") or "(no thought)"
        act_hist    = [x for x in (st.get("operation"), st.get("action")) if x]
        mem_text    = st.get("memory") or ""
        fin_thought = st.get("reflection") or st.get("planning") or ""
        

        screenshot_path = st.get("screenshot")
        if screenshot_path:
            if os.path.isabs(screenshot_path):
                shot_b64 = img_to_b64(screenshot_path)
            else:
                shot_b64 = img_to_b64(shots / screenshot_path)
        else:
            shot_b64 = None

        example = {
            "step_id"   : st["step_id"],
            "mode"      : st["mode"],           
            "thought"   : st.get("thought"),
            "operation" : st.get("operation"),
            "action"    : st.get("action"),
            "memory"    : st.get("memory"),
            "reflection": st.get("reflection"),
            "planning"  : st.get("planning"),
            "screenshot": shot_b64              
        }
        examples.append(example)

    return examples


def generate_html(run_dir, model, run, task, out_root="plots"):
    run_dir  = Path(run_dir)
    examples = steps_to_examples(run_dir)
    
    html = template.render(examples=examples)

    out_path = Path(out_root) / task
    out_path.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    file_ = out_path / f"{model}_{timestamp}.html"
    file_.write_text(html, encoding="utf-8")
    return file_


