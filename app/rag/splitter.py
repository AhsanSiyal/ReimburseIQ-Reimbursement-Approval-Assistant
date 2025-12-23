import re
from typing import List, Dict

RULE_ID_RE = re.compile(r"\bR-[A-Z]{2,5}-\d{3}\b")

def split_markdown_by_headings(md: str, max_chars: int = 2400) -> List[Dict]:
    """
    Splits markdown into chunks by headings, further splitting large sections.
    Returns list of dict chunks with fields: text, section_title, rule_ids
    """
    lines = md.splitlines()
    chunks = []
    current_title = "Untitled"
    buf = []

    def flush():
        nonlocal buf, current_title
        if not buf:
            return
        text = "\n".join(buf).strip()
        if not text:
            buf = []
            return

        # If too large, split by paragraphs
        if len(text) > max_chars:
            parts = re.split(r"\n\s*\n", text)
            part_buf = []
            cur_len = 0
            for p in parts:
                p2 = p.strip()
                if not p2:
                    continue
                if cur_len + len(p2) + 2 > max_chars and part_buf:
                    t = "\n\n".join(part_buf)
                    chunks.append({
                        "text": t,
                        "section_title": current_title,
                        "rule_ids": sorted(set(RULE_ID_RE.findall(t)))
                    })
                    part_buf = [p2]
                    cur_len = len(p2)
                else:
                    part_buf.append(p2)
                    cur_len += len(p2) + 2
            if part_buf:
                t = "\n\n".join(part_buf)
                chunks.append({
                    "text": t,
                    "section_title": current_title,
                    "rule_ids": sorted(set(RULE_ID_RE.findall(t)))
                })
        else:
            chunks.append({
                "text": text,
                "section_title": current_title,
                "rule_ids": sorted(set(RULE_ID_RE.findall(text)))
            })
        buf = []

    for ln in lines:
        if ln.startswith("#"):
            flush()
            current_title = ln.lstrip("#").strip() or "Untitled"
            buf = [ln]
        else:
            buf.append(ln)

    flush()
    return chunks
