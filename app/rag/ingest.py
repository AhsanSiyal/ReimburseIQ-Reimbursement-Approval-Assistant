import os, json
from typing import List, Dict
import numpy as np
import faiss
from openai import OpenAI

from app.core.config import settings
from app.rag.splitter import split_markdown_by_headings

def read_all_markdown(policy_dir: str) -> List[Dict]:
    docs = []
    for root, _, files in os.walk(policy_dir):
        for fn in files:
            if fn.lower().endswith(".md"):
                path = os.path.join(root, fn)
                with open(path, "r", encoding="utf-8") as f:
                    docs.append({"path": path, "text": f.read()})
    return docs

def embed_texts(client: OpenAI, texts: List[str]) -> np.ndarray:
    # Embeddings API supports list input. :contentReference[oaicite:3]{index=3}
    resp = client.embeddings.create(
        model=settings.OPENAI_EMBED_MODEL,
        input=texts
    )
    vecs = np.array([d.embedding for d in resp.data], dtype="float32")
    # Normalize for cosine similarity via inner product
    faiss.normalize_L2(vecs)
    return vecs

def build_faiss_index(vectors: np.ndarray) -> faiss.Index:
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine if vectors are normalized
    index.add(vectors)
    return index

def ingest_policies(policy_dir: str = "data/policies") -> None:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    os.makedirs(os.path.dirname(settings.VECTOR_INDEX_PATH), exist_ok=True)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    raw_docs = read_all_markdown(policy_dir)

    chunks = []
    for d in raw_docs:
        for ch in split_markdown_by_headings(d["text"], max_chars=settings.MAX_POLICY_CHUNK_CHARS):
            chunks.append({
                "source_path": d["path"],
                "section_title": ch["section_title"],
                "rule_ids": ch["rule_ids"],
                "text": ch["text"]
            })

    texts = [c["text"] for c in chunks]
    vectors = embed_texts(client, texts)
    index = build_faiss_index(vectors)

    faiss.write_index(index, settings.VECTOR_INDEX_PATH)
    with open(settings.VECTOR_META_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"[OK] Ingested {len(chunks)} chunks from {policy_dir}")
    print(f"[OK] Wrote index to {settings.VECTOR_INDEX_PATH}")
    print(f"[OK] Wrote metadata to {settings.VECTOR_META_PATH}")
