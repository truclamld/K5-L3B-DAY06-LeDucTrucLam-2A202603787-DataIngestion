"""Read PDF pages and normalize extracted text."""
import unicodedata
from pathlib import Path
from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """TODO: extract each physical page; keep its page number and source.

    Detect and record pages with no text. OCR, when needed, is a separate step.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install the PDF dependency with `pip install -r requirements.txt`.") from exc
    reader = PdfReader(str(path))
    pages = []
    for number, pdf_page in enumerate(reader.pages, start=1):
        raw = pdf_page.extract_text() or ""
        text = normalize_text(raw)
        pages.append(DocumentPage(
            document_id=document_id, source=source, page=number, text=text,
            metadata={"empty": not bool(text), "physical_page": number},
        ))
    return pages


def normalize_text(text: str) -> str:
    """TODO: normalize Unicode and whitespace without discarding useful structure."""
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    lines = [" ".join(line.split()) for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    # Preserve paragraph boundaries while dropping empty runs and PDF noise.
    output = []
    for line in lines:
        if line:
            output.append(line)
        elif output and output[-1] != "":
            output.append("")
    return "\n".join(output).strip()
