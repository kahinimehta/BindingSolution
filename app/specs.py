"""Extract plain text from an uploaded project specification.

Accepts PDF, Markdown, or plain text. Used so a researcher can drop in a
grant aim, proposal, or one-paragraph description and have each paper
assessed against it.
"""
from __future__ import annotations

import io


def extract_text(filename: str, raw: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _from_pdf(raw)
    # Markdown / txt / anything else: decode as UTF-8, tolerant of junk bytes.
    return raw.decode("utf-8", errors="replace").strip()


def _from_pdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf is required to read PDF specs.") from exc

    reader = PdfReader(io.BytesIO(raw))
    chunks = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n\n".join(chunks).strip()
    if not text:
        raise RuntimeError("Could not extract any text from this PDF (it may be scanned images).")
    return text
