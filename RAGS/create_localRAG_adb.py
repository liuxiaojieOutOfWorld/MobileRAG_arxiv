from __future__ import annotations
import re
import json, sys
from pathlib import Path
from typing import List, Dict, Any
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bs4 import BeautifulSoup
from google_play_scraper import app as gp_app   

from FAISS_create import rag
from get_pkg import get_clickable_icon_packages
from play_store_about import get_about_adb
from config import ADB_PATH, LOCALRAG_DATA_FILE, INDEX_DIR



ADB_PATH = ADB_PATH
SAVE_JSON_FILE = LOCALRAG_DATA_FILE
INDEX_DIR = INDEX_DIR





def build_jsonl(records: List[Dict[str, Any]], out_path: str) -> None:
    """Write records list → JSONL (one object per line)."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"✅ JSONL saved → {p.resolve()}  |  total records: {len(records)}")


def main() -> None:
    print("📦 Detecting launchable apps …")
    clickable_pkgs = get_clickable_icon_packages(ADB_PATH)
    print(f"   Found {len(clickable_pkgs)} launchable packages.")

    print("🔍 Querying Google Play …")
    records: List[Dict[str, Any]] = []
    for idx, pkg in enumerate(clickable_pkgs, start=1):
        app_name, about = get_about_adb(pkg)
        if app_name == "none" and about == "none":
            print(f"   [!] {pkg}: Play info not found.")
        records.append({
            "id": idx,
            "pkg": pkg,
            "app_name": app_name,
            "description": about,
        })

    build_jsonl(records, SAVE_JSON_FILE)

    print("🧠 Building FAISS vector index …")
    rag(SAVE_JSON_FILE, INDEX_DIR)
    print(f"🎉 Done. Index saved to {Path(INDEX_DIR).resolve()}")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError:
        sys.stderr.write("adb not  found，pls make sure Android Platform-Tools is installed and ADB_PATH is configured.\n")
        sys.exit(1)