import json
from typing import List, Dict, Any
import numpy as np
import faiss
from openai import OpenAI

from app.core.config import settings

class PolicyRetriever:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.index = faiss.read_index(settings.VECTOR_INDEX_PATH)
        with open(settings.VECTOR_META_PATH, "r", encoding="utf-8") as f:
            self.meta = json.load(f)

    def _embed(self, text: str) -> np.ndarray:
        resp = self.client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=[text]
        )
        v = np.array(resp.data[0].embedding, dtype="float32")[None, :]
        faiss.normalize_L2(v)
        return v

    def search(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        k = top_k or settings.RAG_TOP_K
        qv = self._embed(query)
        scores, idxs = self.index.search(qv, k)

        out = []
        for score, i in zip(scores[0].tolist(), idxs[0].tolist()):
            if i < 0:
                continue
            m = self.meta[i]
            out.append({
                "score": float(score),
                "source_path": m["source_path"],
                "section_title": m["section_title"],
                "rule_ids": m["rule_ids"],
                "text": m["text"]
            })
        return out
