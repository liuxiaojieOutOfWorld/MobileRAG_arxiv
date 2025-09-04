from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Callable
import os
import time
import sys
sys.path.append(str(Path(__file__).parent.parent))  
from config import MEM_DIR, MEM_JSON  

from langchain.docstore.document import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

def _load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _to_app_documents(data: List[Dict[str, Any]]) -> List[Document]:
    docs = []
    for item in data:
        desc = item.get("description", "").strip()
        if desc:
            docs.append(Document(page_content=desc, metadata={"id": item["id"]}))
    return docs

#new added
def _to_mem_documents(data: List[Dict[str, Any]]) -> List[Document]:
    docs = []
    for item in data:
        task = str(item.get("task", "")).strip()
        if task:
            docs.append(Document(page_content=task,
                                 metadata={"id": item.get("id")}))
    return docs

def rag(
        save_json_file, 
        index_dir,

        to_doc_fn: Callable[[List[Dict[str, Any]]], List[Document]] = _to_app_documents,

        ) -> None:
    try:
        max_retries = 3
        retry_delay = 5  
        
        for attempt in range(max_retries):
            try:
                print(f"Attempting download (number {attempt + 1} time)...")
                embeddings = HuggingFaceEmbeddings(
                    model_name=EMBEDDING_MODEL,
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Download Failure: {str(e)}")
                    print("Using Downloaded model...")
                    model_path = "./models/BAAI/bge-small-en-v1.5"
                    if not os.path.exists(model_path):
                        os.makedirs(model_path, exist_ok=True)
                    embeddings = HuggingFaceEmbeddings(
                        model_name=model_path,
                        model_kwargs={'device': 'cpu'},
                        encode_kwargs={'normalize_embeddings': True}
                    )
                else:
                    print(f"Download Failure，retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
        
        data = _load_jsonl(save_json_file)
        if not data:
            raise ValueError(f"[RAG] no valid data in {save_json_file}")
            
        docs = to_doc_fn(data)
        if not docs:
            raise ValueError("[RAG] no description field found")
            
        vectorstore = FAISS.from_documents(docs, embeddings)
        vectorstore.save_local(index_dir)
        print(f"✅ RAG index saved to {index_dir}")
        
    except Exception as e:
        print(f"❌ RAG create failure: {str(e)}")
        raise



if __name__ == "__main__":
    
    mem_dir = MEM_DIR
    mem_json = MEM_JSON
    rag(mem_json, mem_dir, to_doc_fn = _to_mem_documents)