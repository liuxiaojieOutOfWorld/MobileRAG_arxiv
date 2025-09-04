import json
from pathlib import Path

def append_to_memrag_ndjson(
    steps_path: Path,
    task_name: str,
    mem_file: Path
) -> None:



    if not steps_path.exists():
        raise FileNotFoundError(f"no {steps_path}")

    with steps_path.open(encoding="utf-8") as f:
        steps = json.load(f)


    actions = [
        s.get("action")
        for s in sorted(steps, key=lambda x: x.get("step_id", 0))
        if s.get("action")
    ]


    next_id = 1
    if mem_file.exists() and mem_file.stat().st_size > 0:
        with mem_file.open(encoding="utf-8") as f:
            ids = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and "id" in obj:
                        ids.append(int(obj["id"]))
                except json.JSONDecodeError:
                    continue
            if ids:
                next_id = max(ids) + 1


    entry = {"id": next_id, "task": task_name, "action": actions}
    line = json.dumps(entry, ensure_ascii=False) + "\n"


    mem_file.parent.mkdir(parents=True, exist_ok=True)
    with mem_file.open("a", encoding="utf-8") as f:
        f.write(line)
        f.write("\n")
        f.flush()  
