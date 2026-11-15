"""Parse pdf/docx/markdown and split into chunks."""

from __future__ import annotations

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


class EmptyDocumentError(ValueError):
    """Raised when a file yields no extractable text."""


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts).strip()


def extract_docx_text(path: Path) -> str:
    from docx import Document as DocxDocument

    doc = DocxDocument(str(path))
    parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n\n".join(parts).strip()


def extract_text(path: Path, *, filename: str | None = None) -> str:
    name = (filename or path.name).lower()
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        text = extract_pdf_text(path)
    elif suffix == ".docx":
        text = extract_docx_text(path)
    elif suffix in {".md", ".markdown"}:
        text = read_text_file(path).strip()
    else:
        raise ValueError(f"unsupported file type: {suffix}")
    if not text:
        raise EmptyDocumentError("无法提取文本（可能是扫描件或空文档）")
    return text


def split_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    chunks = [c.strip() for c in splitter.split_text(text) if c.strip()]
    if not chunks:
        raise EmptyDocumentError("切分后无可用文本片段")
    return chunks


def parse_and_split(path: Path, *, filename: str | None = None) -> list[str]:
    return split_text(extract_text(path, filename=filename))
