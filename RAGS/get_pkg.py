import subprocess
from typing import List
from pathlib import Path
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LOCALRAG_DATA_FILE

JSON_PATH = LOCALRAG_DATA_FILE

def adb(cmd: str, ADB_PATH) -> str:
    """Run adb sub-command and return stdout (str)."""
    return subprocess.check_output(
        [ADB_PATH] + cmd.split(),
        stderr=subprocess.DEVNULL,
        text=True
    ).strip()

def list_all_packages(ADB_PATH) -> List[str]:
    """Return every package name on the device (system + user)."""
    raw = adb("shell pm list packages", ADB_PATH)
    return [line.split(":", 1)[1] for line in raw.splitlines()]

def has_launcher_icon(pkg: str, ADB_PATH) -> bool:
    """Does the package have a Launcher Activity (= a clickable icon)?"""
    try:
        result = adb(f"shell cmd package resolve-activity --brief {pkg}", ADB_PATH)
        return "/" in result
    except subprocess.CalledProcessError:
        return False

def get_clickable_icon_packages(ADB_PATH) -> List[str]:
    """Return sorted list of packages with launcher icons (sequential)."""
    pkgs = list_all_packages(ADB_PATH)
    return sorted([p for p in pkgs if has_launcher_icon(p, ADB_PATH)])


