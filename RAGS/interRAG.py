# web_search.py
import json
import re
from pathlib import Path
from typing import Literal, Optional

import requests
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import GOOGLE_KEY, GOOGLE_CX


def _safe_query(q: str) -> str:
    return re.sub(r"[^\w\-]+", "_", q.strip())[:60] or "query"

def search_google(api_key: str, cx: str, query: str) -> dict:
    url    = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query}
    return requests.get(url, params=params).json()

def search_bing(api_key: str, query: str) -> dict:
    url     = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params  = {"q": query, "textDecorations": True}
    return requests.get(url, headers=headers, params=params).json()


def save_json(data: dict, path: Path) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def simplify_google_json(google_json_path: Path, out_path: Path) -> Path:
    data = json.loads(google_json_path.read_text(encoding="utf-8"))

    simplified = []
    for item in data.get("items", []):
        simple = {
            "title":       item.get("title"),
            "snippet":     item.get("snippet"),
            "link":        item.get("link"),
            "displayLink": item.get("displayLink"),
        }
        og_descr = item.get("pagemap", {}).get("metatags", [{}])[0].get("og:description")
        if og_descr:
            simple["og_description"] = og_descr
        simplified.append(simple)

    save_json({"results": simplified}, out_path)
    return out_path


def api_search(
    query: str,
    api:   Literal["google", "bing"] = "google",
    *,
    google_key: Optional[str] = None,
    google_cx:  Optional[str] = None,
    bing_key:   Optional[str] = None,
    out_dir:    str           = "./search_results",
) -> Path:

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    q_safe  = _safe_query(query)

    if api == "google":
        if not (google_key and google_cx):
            raise ValueError("google_key / google_cx required for Google search")
        data = search_google(google_key, google_cx, query)
        file_path = out_dir / f"google_{q_safe}.json"

    elif api == "bing":
        if not bing_key:
            raise ValueError("bing_key required for Bing search")
        data = search_bing(bing_key, query)
        file_path = out_dir / f"bing_{q_safe}.json"

    else:
        raise ValueError("api must be 'google', 'bing' or 'wiki'")

    return save_json(data, file_path)

# ------------------ demo: end‑to‑end ------------------ #
if __name__ == "__main__":
    # ===== config =====
    QUERY      = "squid game where to watch"
    API_NAME   = "google"               # "google" | "bing"
    # ==========================

    # 1. find and save JSON
    full_json_path = api_search(
        QUERY,
        api=API_NAME,
        google_key=GOOGLE_KEY,
        google_cx=GOOGLE_CX,
        # bing_key="YOUR_BING_KEY"      
    )
    print(f"✔ full JSON saved to {full_json_path}")
    
    if API_NAME == "google":
        simplified_path = full_json_path.with_name("simplified_" + full_json_path.name)
        simplify_google_json(full_json_path, simplified_path)
        print(f"✔ simplified JSON saved to {simplified_path}")