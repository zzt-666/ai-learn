"""Pure helpers for knowledge-base ownership quotas and file validation."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS = frozenset({".pdf", ".docx", ".md", ".markdown"})


def normalize_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def is_supported_filename(filename: str) -> bool:
    return normalize_extension(filename) in SUPPORTED_EXTENSIONS


def check_file_size(size_bytes: int, *, max_bytes: int) -> None:
    if size_bytes <= 0:
        raise ValueError("file is empty")
    if size_bytes > max_bytes:
        raise ValueError(f"file exceeds max size of {max_bytes} bytes")


def check_base_quota(current_count: int, *, max_bases: int) -> None:
    if current_count >= max_bases:
        raise ValueError(f"knowledge base quota exceeded (max {max_bases})")


def check_document_quota(current_count: int, *, max_docs: int) -> None:
    if current_count >= max_docs:
        raise ValueError(f"document quota exceeded (max {max_docs})")


def content_type_for_filename(filename: str) -> str:
    ext = normalize_extension(filename)
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
    }.get(ext, "application/octet-stream")
