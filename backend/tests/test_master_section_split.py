from __future__ import annotations

from app.services.master_section_split import (
    split_by_headings,
    split_by_paragraph_aggregation,
    split_into_sections,
)


def test_headed_markdown_yields_titled_sections():
    text = """# 绪论

开场白一段。

## 第一章 基础

基础内容很多字。

## 第二章 进阶

进阶内容也很多。
"""
    sections = split_into_sections(text)
    assert len(sections) >= 2
    titles = [s.title for s in sections]
    assert any("基础" in t or "第一章" in t for t in titles)
    assert any("进阶" in t or "第二章" in t for t in titles)
    assert split_by_headings(text) is not None


def test_chinese_chapter_headings():
    text = "第1章 概述\n\n概述正文。\n\n第2章 细节\n\n细节正文。"
    sections = split_by_headings(text)
    assert sections is not None
    assert len(sections) == 2
    assert "概述" in sections[0].title
    assert "细节" in sections[1].title


def test_prose_uses_paragraph_aggregation():
    para = "这是一段没有标题的散文。" * 40  # ~400 chars each * few
    text = "\n\n".join([para, para, para, para])
    sections = split_into_sections(text)
    assert sections
    assert all(s.title.startswith("第") for s in sections)
    assert split_by_headings(text) is None
    aggregated = split_by_paragraph_aggregation(text, min_chars=200, max_chars=900)
    assert len(aggregated) >= 1
    assert sum(len(s.body) for s in aggregated) >= len(text) - 50
