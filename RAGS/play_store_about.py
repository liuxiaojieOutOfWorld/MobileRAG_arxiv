# play_store_about
# -------------------------------------------------
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json, re
import subprocess
import time
from bs4 import BeautifulSoup
import requests
from config import ADB_PATH

from google_play_scraper import search, app      


DEFAULT_PREFER_DEV = {
    "calculator": "Google LLC",
    "phone":      "Google LLC",
    "clock":      "Google LLC",
    "maps":       "Google LLC",
    "camera":     "Google LLC",
    "photos":     "Google LLC",
    "messages":   "Google LLC",
    "safety":     "Google LLC",
    "contacts":   "Google LLC",

}



def choose_app_id(keyword   : str,
                  prefer_dev: Optional[str] = None,
                  lang      : str = "en",
                  country   : str = "us") -> str:
    prefer_dev = prefer_dev or DEFAULT_PREFER_DEV.get(keyword.lower())
    hits = search(keyword, lang=lang, country=country, n_hits=10)
    if not hits:
        raise ValueError(f"[Play] no result for '{keyword}'")

    keyword_low = keyword.lower()

    if prefer_dev:
        for h in hits:
            if (prefer_dev.lower() == h["developer"].lower() and 
                h["title"].lower() == keyword_low):
                return h["appId"]

    if prefer_dev:
        for h in hits:
            if (prefer_dev.lower() == h["developer"].lower() and 
                h["title"].lower().startswith(keyword_low)):
                return h["appId"]

    if prefer_dev:
        for h in hits:
            if (prefer_dev.lower() == h["developer"].lower() and 
                keyword_low in h["title"].lower()):
                return h["appId"]

    for h in hits:
        if h["title"].lower() == keyword_low:
            return h["appId"]

    return hits[0]["appId"]


_TAG_RE = re.compile(r"<[^>]+>")        

def fetch_about_text(app_id  : str,
                     lang    : str = "en",
                     country : str = "us") -> str:
    info    = app(app_id, lang=lang, country=country)
    summary = info.get("summary", "").strip()
    body    = info.get("descriptionHTML", "")

    if body:
        try:
            body = BeautifulSoup(body, "html.parser").get_text("\n").strip()
        except Exception:                      
            body = _TAG_RE.sub("", body).strip()

    return (summary + "\n\n" + body).strip() if summary else body


# -------- 4. find information / save json --------
def get_about(keyword   : str,
              prefer_dev: Optional[str] = None,
              lang      : str = "en",
              country   : str = "us") -> str:

    app_id = choose_app_id(keyword, prefer_dev, lang, country)
    return fetch_about_text(app_id, lang, country)


def save_about_json(keyword   : str,
                    out_dir: str = "./about_app",
                    prefer_dev: Optional[str] = None,
                    lang      : str = "en",
                    country   : str = "us") -> Path:

    app_id = choose_app_id(keyword, prefer_dev, lang, country)
    about  = fetch_about_text(app_id, lang, country)

    data = {
        "text": f"text: {keyword}",
        "description": about
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fname   = f"{keyword.lower().replace(' ', '_')}_about.json"
    outpath = out_dir / fname
    outpath.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                       encoding="utf-8")

    print(f"✔ saved → {outpath}   (AppId: {app_id})")
    return outpath




_FIXED_APPS: dict[str, Tuple[str, str]] = {
    "com.android.camera2": (
        "Camera",
        "The Camera app is the native photo and video capturing application "
        "developed by Google specifically for Pixel devices. It allows users "
        "to take high-quality photos and videos using various shooting modes "
        "and built-in AI enhancements."
    ),
    "com.android.settings": (
        "Settings",
        "The Settings app is the central control hub on Android devices, used "
        "to manage and customize nearly all aspects of the system. It allows "
        "you to adjust preferences, configure connected devices, control "
        "permissions, and much more."
    ),
    "com.android.stk": (
        "SIM Toolkit",
        "The T-Mobile SIM Toolkit manages SIM-card and network settings "
        "specifically related to your carrier service."
    ),
    "com.android.vending": (
        "Play Store",
        "The Google Play Store is the official digital marketplace for Android. "
        "It's the central hub for downloading and updating apps, games, books, "
        "movies, TV shows, and other content."
    ),
    "com.google.android.documentsui": (
        "Files",
        "The Files app is Google's native file-management tool for Android. "
        "It helps you browse, manage, share, and clean up files on your device."
    ),
}




_TAG_RE = re.compile(r"<[^>]+>")

def _clean_html(html: str) -> str:
    if not html:
        return ""
    try:
        return BeautifulSoup(html, "html.parser").get_text("\n").strip()
    except Exception:
        return _TAG_RE.sub("", html).strip()



def get_about_adb(pkg: str, *, lang: str = "en", country: str = "us") -> Tuple[str, str]:

    if pkg in _FIXED_APPS:
        return _FIXED_APPS[pkg]

    try:
        info = app(pkg, lang=lang, country=country)
        app_name = info.get("title", "").strip()
        summary  = info.get("summary", "").strip()
        body     = _clean_html(info.get("descriptionHTML", ""))

        description_parts = [p for p in (summary, body) if p]
        description = "\n\n".join(description_parts).strip()

        if not app_name or not description:
            raise ValueError("missing field")


        return app_name, description


    except Exception:

        return "none", "none"








