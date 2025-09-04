## MobileRAG_arxiv

A mobile agent that operates an Android device via ADB and solves tasks through Retrieval-Augmented Generation (RAG). It combines: (1) LocalRAG over installed apps, (2) MemRAG over past successful runs, and (3) InterRAG for web search. The agent follows a plan–act–reflect loop, reads the screen (OCR + icon detection + optional multimodal caption), executes actions (tap/swipe/type), and records each step.

- Repository: [MobileRAG_arxiv](https://github.com/liuxiaojieOutOfWorld/MobileRAG_arxiv.git)

---

### Highlights
- End-to-end Android control via ADB: screenshot, tap, swipe, type, back, home.
- Three retrieval sources:
  - LocalRAG (installed apps, FAISS index)
  - InterRAG (Google Custom Search)
  - MemRAG (experience replay from previous runs)
- Multimodal icon descriptions with Qwen-VL (API or local model).
- Plan → Action → Reflection loop with detailed step logs and an HTML run report.

---

### Project layout (key files)
- `config.py`: All configuration (ADB path, APIs/keys, model switches, RAG paths, prompts).
- `rag_run.py`: Main entry. Orchestrates ADB I/O, perception, RAG, dialogue, actions, logging, and report.
- `MobileAgent/`
  - `controller.py`: ADB I/O (screenshot, tap, swipe, type, back, home).
  - `text_localization.py`: OCR detection and recognition.
  - `icon_localization.py`: Icon detection.
  - `chat.py`, `prompt.py`: Dialogue buffers and prompt builders (planning/action/reflection/memory/process).
  - `api.py`: Generic chat API caller (`inference_chat`).
- `RAGS/`
  - `get_pkg.py`, `check_install.py`: Scan installed apps, maintain JSONL records.
  - `FAISS_create.py`: Build/update FAISS indexes (LocalRAG, MemRAG).
  - `rag.py`: Core RAG methods: `query_localrag`, `query_interrag`, `query_memrag`, `load_appname2pkg`.
  - `create_localRAG_adb.py`: First-time collection of device apps to JSONL.
- `rag_records/`: Run logs (JSON steps, screenshots, HTML report).
- `rag_screenshot/`: Latest screenshot (`screenshot.jpg`).
- `temp/`: Temporary crops for icon descriptions.

---

### Requirements
- Python 3.9+
- Android Debug Bridge (ADB)
- Optional: GPU (if using local multimodal models)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

### ADB setup (device or emulator)
1) Enable Developer Options and USB debugging on your Android device. Connect via USB and select “File transfer.”
2) Verify connection:
```bash
adb devices
```
3) macOS/Linux permissions if needed:
```bash
chmod +x /path/to/adb
```
4) On Windows, the ADB path usually looks like: `.../adb.exe`.

---

### ADB Keyboard (optional but recommended)
1) Install `ADBKeyboard.apk` on the device and set it as the default input method.
2) If it does not take effect, enable via ADB:
```bash
adb shell ime enable com.android.adbkeyboard/.AdbIME
adb shell settings put secure default_input_method com.android.adbkeyboard/.AdbIME
adb shell settings get secure default_input_method
```

---

### Android Studio (optional)
- Platform Tools includes ADB.
- Check SDK path in Settings → Languages & Frameworks → Android SDK.
- For emulators, install ADB Keyboard by uploading the APK in Device Explorer to `/storage/emulated/0/Download` and install it.

---

### Configuration (`config.py`)
Fill in what you need:
- ADB
  - `ADB_PATH`: path to your adb binary.
- Chat/LLM API
  - `API_URL`, `API_TOKEN`: your OpenAI-compatible endpoint.
  - `QWEN_API`: DashScope API key for Qwen-VL when using icon descriptions.
  - `CAPTION_CALL_METHOD`: `"api"` or `"local"`.
  - `CAPTION_MODEL`:
    - `api`: `qwen-vl-plus`, `qwen-vl-max`
    - `local`: `qwen-vl-chat`, `qwen-vl-chat-int4`
- Google Search (InterRAG)
  - `GOOGLE_KEY`, `GOOGLE_CX`
- RAG paths
  - `INDEX_DIR`, `LOCALRAG_DATA_FILE`: LocalRAG index and JSONL.
  - `MEM_DIR`, `MEM_JSON`: MemRAG index and JSONL.
- Switches
  - `REFLECTION_SWITCH`, `MEMORY_SWITCH`: enable/disable reflection and memory units.
- Prompt add-ons
  - `ADD_INFO`, `ADD_INFO_PLAN`: extra operating rules and planning priorities (pre-filled but editable).

---

### Build LocalRAG & MemRAG (first run)
1) Scan device apps and create JSONL:
```bash
python RAGS/create_localRAG_adb.py
```
2) Build FAISS indexes (LocalRAG & MemRAG):
```bash
python RAGS/FAISS_create.py
```
LocalRAG answers “is an app installed / basic app info”, while MemRAG stores successful task experiences and is rebuilt after each run.

---

### Quickstart
1) Configure `config.py` (ADB path, API URL/token, Qwen-VL key, caption method/model, Google keys).
2) Set an instruction in `rag_run.py`, for example:
```python
instruction = "open Google Maps."
```
3) Run the agent:
```bash
python rag_run.py
```
During the run:
- The loop Plan → Action → Reflection progresses the task.
- Screenshots and steps are written to `rag_records/` (`steps.json` + images).
- On finish, the run is appended to `memRAG/memrag_data.jsonl` and the FAISS index is rebuilt.
- An HTML report is generated (its path is printed in the console by `plot.generate_html`).

---

### How it works (mapped to code)
- Perception: `MobileAgent.controller.get_screenshot` + OCR (`text_localization.py`) + icon detection (`icon_localization.py`) + optional icon captions (Qwen-VL).
- Retrieval:
  - `RAGS.rag.query_localrag(term, index_dir, json_path)`
  - `RAGS.rag.query_interrag(query)`
  - `RAGS.rag.query_memrag(instruction, mem_dir, mem_json)`
  - `RAGS.rag.load_appname2pkg(json_path)`
- Actions: `MobileAgent.controller.tap/slide/type/back/home` (press Enter after typing when a search box is detected).
- Dialogue & prompts: chat buffers in `MobileAgent.chat`, prompts in `prompt.py`, model inference via `MobileAgent.api.inference_chat`.
- Logging & report: `rag_records/steps.json` updated continuously; final HTML report via `plot.py`.

---

### Troubleshooting
- API/network errors: check `API_URL`, `API_TOKEN`, connectivity; see prints from `MobileAgent/api.py`.
- GPU memory issues for local Qwen-VL: use `CAPTION_CALL_METHOD = "api"` or `qwen-vl-chat-int4`.
- No LocalRAG hits: ensure `RAGS/create_localRAG_adb.py` and `RAGS/FAISS_create.py` were executed and paths in `config.py` are correct.
- Input not typed: ensure ADB Keyboard is enabled, or focus a text field before `Type`.

---

### License & citation
- For research/education only. Ensure compliance with data and privacy policies in your jurisdiction.
- If you use this repository, please cite/link:
  - [MobileRAG_arxiv](https://github.com/liuxiaojieOutOfWorld/MobileRAG_arxiv.git)