"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """TODO: split text into overlapping windows and retain page metadata."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("size must be positive and 0 <= overlap < size")
    text = page.text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # Prefer a nearby word boundary without creating tiny chunks.
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        body = text[start:end].strip()
        if body:
            chunks.append(Chunk(f"{page.document_id}:{page.page}:fixed:{start}", page.document_id,
                                page.source, page.page, body,
                                {**page.metadata, "char_start": start, "char_end": end}))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """TODO: group paragraphs, split oversized paragraphs and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
    groups = []
    current = ""
    for paragraph in paragraphs:
        pieces = [paragraph[i:i + max_size] for i in range(0, len(paragraph), max_size)]
        for piece in pieces:
            if current and len(current) + 2 + len(piece) > max_size:
                groups.append(current)
                current = ""
            current = f"{current}\n\n{piece}" if current else piece
    if current:
        groups.append(current)
    return [Chunk(f"{page.document_id}:{page.page}:paragraph:{i}", page.document_id,
                  page.source, page.page, body,
                  {**page.metadata, "chunk_index": i, "chunking": "paragraph"})
            for i, body in enumerate(groups)]
