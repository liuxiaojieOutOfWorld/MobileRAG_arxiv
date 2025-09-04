import json, re, requests
from typing import List, Dict, Any
from pathlib import Path
from functools import lru_cache
# from config import LOCALRAG_DATA_FILE, INDEX_DIR

from langchain.docstore.document     import Document
from langchain_community.embeddings import HuggingFaceEmbeddings   # 
from langchain_community.vectorstores import FAISS
from config import GOOGLE_KEY, GOOGLE_CX

@lru_cache(maxsize=1)
def _load_vector_store(INDEX_DIR):
    INDEX_DIR = Path(INDEX_DIR)
    emb = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    vs  = FAISS.load_local(INDEX_DIR, emb, allow_dangerous_deserialization=True)
    return vs

@lru_cache(maxsize=1)
def _load_json_records(JSON_PATH):
    records = {}
    JSON_PATH = Path(JSON_PATH)
    with JSON_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            records[d["id"]] = d
    return records


def query_localrag(term: str, INDEX_DIR, JSON_PATH, *, top_k: int = 3) -> str:
    vs        = _load_vector_store(INDEX_DIR)
    json_recs = _load_json_records(JSON_PATH)

    hits = vs.similarity_search(term, k=top_k)

    if not hits:
        return f"[LocalRAG] no hit for \"{term}\"."

    lines = []
    for h in hits:
        print("hit id:", h.metadata.get("id"))
        rid = h.metadata.get("id")
        rec = json_recs.get(rid)
        lines.append(
            '{'
            f'"id": {rid}, '
            f'"pkg": "{rec["pkg"]}", '
            f'"app_name": "{rec["app_name"]}",'
            f'"description": {rec["description"]}'
            '}'
        )  
        if not rec:               
            continue


 

    return "\n".join(lines) if lines else f"[LocalRAG] no valid record for \"{term}\"."





def _safe_query(q: str) -> str:
    return re.sub(r"[^\w\-]+", "_", q.strip())[:60] or "query"

def _google_search(api_key: str, cx: str, query: str) -> dict:
    url    = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": 10}
    return requests.get(url, params=params, timeout=15).json()


def query_interrag(query: str, *, top_k: int = 10) -> str:
    raw = _google_search(GOOGLE_KEY, GOOGLE_CX, query)

    items: List[dict] = raw.get("items", [])[:top_k]
    if not items:
        return f"[InterRAG] no hit for \"{query}\"."

    lines = []
    for it in items:
        simple = {
            "title":       it.get("title"),
            "snippet":     it.get("snippet"),
            "link":        it.get("link"),
            "displayLink": it.get("displayLink"),
        }
        og_descr = (
            it.get("pagemap", {})
              .get("metatags", [{}])[0]
              .get("og:description")
        )
        if og_descr:

            simple["og_description"] = og_descr.replace("\\", "\\\\").replace("\n", "\\n")

        lines.append(json.dumps(simple, ensure_ascii=False))

    return "\n".join(lines)



def load_appname2pkg(json_path: str) -> dict[str, str]:
    mapping: Dict[str, str] = {}

    with Path(json_path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                mapping[obj["app_name"].lower()] = obj["pkg"]

    return mapping






def query_memrag(term: str, INDEX_DIR: str, JSON_PATH: str) -> str:
    vs        = _load_vector_store(INDEX_DIR)
    json_recs: Dict[int, Dict[str, Any]] = _load_json_records(JSON_PATH)

    hits = vs.similarity_search_with_score(term, k=1)
    if not hits:
        return f"[memRAG] no hit for \"{term}\"."

    doc, score = hits[0]
    rid = doc.metadata.get("id")
    print("hit id:", rid, "score:", score)

    rec = json_recs.get(rid)
    if rec is None:
        return f"[memRAG] hit id={rid} not found in JSON records."

    score = float(score)

    result = {
        "task":   rec.get("task"),
        "action": rec.get("action"),
        "score":  score
    }
    return result


