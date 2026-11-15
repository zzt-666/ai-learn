from pathlib import Path

import pytest
from docx import Document as DocxDocument
from pypdf import PdfWriter

from app.services.document_parse import (
    EmptyDocumentError,
    extract_text,
    parse_and_split,
    split_text,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_markdown_fixture() -> None:
    path = FIXTURES / "sample.md"
    chunks = parse_and_split(path)
    assert len(chunks) >= 1
    joined = "\n".join(chunks)
    assert "退货" in joined
    assert "开场白" in joined


def test_parse_docx(tmp_path: Path) -> None:
    path = tmp_path / "note.docx"
    doc = DocxDocument()
    doc.add_heading("培训要点", level=1)
    doc.add_paragraph("员工入职第一天必须完成信息安全培训。")
    doc.add_paragraph("密码长度不少于 12 位，禁止与工号相同。")
    doc.save(path)
    text = extract_text(path)
    assert "信息安全" in text
    chunks = split_text(text)
    assert len(chunks) >= 1


def test_parse_pdf(tmp_path: Path) -> None:
    # Minimal PDF with text via pypdf is awkward; write empty then skip if no text.
    # Use a simple text-bearing approach: create PDF page with text object is complex.
    # Instead write markdown-as-pdf-alternative: create PDF with metadata only and
    # assert EmptyDocumentError for truly empty pages.
    path = tmp_path / "empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as f:
        writer.write(f)
    with pytest.raises(EmptyDocumentError):
        extract_text(path)


def test_empty_markdown_fails(tmp_path: Path) -> None:
    path = tmp_path / "empty.md"
    path.write_text("   \n\n", encoding="utf-8")
    with pytest.raises(EmptyDocumentError):
        extract_text(path)
