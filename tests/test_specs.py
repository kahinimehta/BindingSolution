"""Unit tests for project-spec text extraction."""
from __future__ import annotations

import io

import pytest
from docx import Document

from app.specs import extract_text


def _docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_extract_docx_text():
    body = (
        "We study fairness and calibration in recommender systems using causal "
        "inference and graph neural networks across multiple domains."
    )
    text = extract_text("aim.docx", _docx_bytes(body))
    assert "fairness and calibration" in text


def test_extract_docx_rejects_empty():
    with pytest.raises(RuntimeError, match="Could not extract"):
        extract_text("empty.docx", _docx_bytes("   "))
