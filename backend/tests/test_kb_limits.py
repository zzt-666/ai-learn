import pytest

from app.services.kb_limits import (
    check_base_quota,
    check_document_quota,
    check_file_size,
    is_supported_filename,
)


def test_supported_extensions() -> None:
    assert is_supported_filename("a.PDF")
    assert is_supported_filename("notes.md")
    assert is_supported_filename("x.markdown")
    assert is_supported_filename("doc.docx")
    assert not is_supported_filename("x.exe")
    assert not is_supported_filename("image.png")


def test_file_size_limits() -> None:
    check_file_size(100, max_bytes=1024)
    with pytest.raises(ValueError, match="empty"):
        check_file_size(0, max_bytes=1024)
    with pytest.raises(ValueError, match="max size"):
        check_file_size(2048, max_bytes=1024)


def test_base_and_doc_quotas() -> None:
    check_base_quota(9, max_bases=10)
    with pytest.raises(ValueError, match="knowledge base quota"):
        check_base_quota(10, max_bases=10)
    check_document_quota(19, max_docs=20)
    with pytest.raises(ValueError, match="document quota"):
        check_document_quota(20, max_docs=20)
