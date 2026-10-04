"""Split long documents into overlapping windows.

Chunking helps retrieval: a query about 'React' should match a small resume
passage, not force the model to embed the entire file as one vector.
Paragraphs are kept together when they fit, then long blocks are windowed.
"""

import re


def _window(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        window = text[start:end]
        if end < length:
            last_space = window.rfind(" ")
            if last_space > chunk_size // 3:
                end = start + last_space
                window = text[start:end]
        piece = window.strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_text(
    text: str,
    *,
    chunk_size: int = 400,
    overlap: int = 80,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    blocks = [
        " ".join(part.split())
        for part in re.split(r"\n\s*\n", text.strip())
        if part.strip()
    ]
    if not blocks:
        return []

    chunks: list[str] = []
    current = ""
    for block in blocks:
        if len(block) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_window(block, chunk_size, overlap))
            continue
        candidate = f"{current} {block}".strip() if current else block
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            current = block
    if current:
        chunks.append(current)
    return chunks
