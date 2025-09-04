import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess, json
import re
import time
from pathlib import Path
from typing import Set, Tuple, Dict, Any, List
from RAGS.get_pkg import has_launcher_icon
from RAGS.play_store_about import get_about_adb
from RAGS.FAISS_create import rag
from RAGS.rag import load_appname2pkg
from config import ADB_PATH, LOCALRAG_DATA_FILE, INDEX_DIR

def load_existing_records(jsonl_path: str) -> Tuple[Set[str], int]:
    pkgs, max_id = set(), 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            pkgs.add(obj["pkg"])
            max_id = max(max_id, obj["id"])
    return pkgs, max_id



def detect_new_installs(adb_path: str, seen_pkgs: Set[str]) -> Set[str]:

    try:
        log = subprocess.check_output(
            [adb_path, "logcat", "-d", 
             "ProximityAuth:I", "*:S"],
            text=True,
            errors="ignore"          
        )
    except subprocess.CalledProcessError:
        return set()
    
    subprocess.run([adb_path, "logcat", "-c"], stderr=subprocess.DEVNULL)

    new_pkgs: Set[str] = set()
    pattern = re.compile(
        r"package\s+added[:\s]+\(?user[^\)]*\)?\s*([A-Za-z0-9._]+)",
        re.I
    )

    for line in log.splitlines():
        m = pattern.search(line)
        if not m:
            continue
        pkg = m.group(1)
        if pkg and pkg not in seen_pkgs:
            new_pkgs.add(pkg)

    return new_pkgs


def append_record(jsonl_path: str, record: Dict[str, Any]) -> None:
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def handle_new_installs(existing_pkgs: Set[str],
                        next_id: int,
                        adb_path: str,
                        save_json_file: str,
                        index_dir: str) -> Tuple[Set[str], Set[str], int]:

    new_pkgs = detect_new_installs(adb_path, existing_pkgs)
    if not new_pkgs:
        return existing_pkgs, next_id



    truly_new: List[str] = []
    for pkg in new_pkgs:
        if not has_launcher_icon(pkg, adb_path):   
            continue
        truly_new.append(pkg)

    if not truly_new:
        return existing_pkgs, next_id

    for pkg in truly_new:
        app_name, about = get_about_adb(pkg)
        next_id += 1
        record = {
            "id": next_id,
            "pkg": pkg,
            "app_name": app_name,
            "description": about
        }
        with open(save_json_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"[NEW] Added to JSONL → {pkg} ({app_name})")
        existing_pkgs.add(pkg)

    print("🧠 Rebuilding FAISS index (new app detected)…")
    rag(save_json_file, index_dir)
    print("✔ FAISS index update done.\n")

    return existing_pkgs, next_id



if __name__ == "__main__":
    adb_path = ADB_PATH
    json_dir = LOCALRAG_DATA_FILE


    seen_pkgs, max_id = load_existing_records(json_dir)   
    print(f"[initializing] Found {len(seen_pkgs)} new installed")


    try:
        while True:
            new_pkgs = detect_new_installs(adb_path, seen_pkgs)
            print(f"new_pkgs  ({len(new_pkgs)}): {sorted(new_pkgs)}")
            print(f"seen_pkgs ({len(seen_pkgs)}): {sorted(seen_pkgs)}")
            if new_pkgs:
                print(f"[+] Found new installed: {', '.join(sorted(new_pkgs))}")
                seen_pkgs.update(new_pkgs)
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nDone Scanning。")