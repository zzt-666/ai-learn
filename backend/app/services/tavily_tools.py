"""Official Tavily tool assembly for quiz web grounding."""

from __future__ import annotations

from langchain_tavily import TavilyExtract, TavilySearch

DEFAULT_MAX_RESULTS = 5


def build_tavily_search(*, api_key: str) -> TavilySearch:
    """Global keyword search with summary-only defaults (no raw content)."""
    return TavilySearch(
        name="tavily_search",
        max_results=DEFAULT_MAX_RESULTS,
        topic="general",
        include_raw_content=False,
        include_answer=False,
        tavily_api_key=api_key,
    )


def build_tavily_search_china(*, api_key: str) -> TavilySearch:
    """Same defaults as global search, boosted toward China results."""
    return TavilySearch(
        name="tavily_search_china",
        max_results=DEFAULT_MAX_RESULTS,
        topic="general",
        include_raw_content=False,
        include_answer=False,
        country="china",
        tavily_api_key=api_key,
    )


def build_tavily_extract(*, api_key: str) -> TavilyExtract:
    """Extract full page content from one or more URLs."""
    return TavilyExtract(
        name="tavily_extract",
        extract_depth="basic",
        include_images=False,
        tavily_api_key=api_key,
    )


def build_quiz_research_tools(*, api_key: str) -> list[TavilySearch | TavilyExtract]:
    """Tools bound to the research agent: global search, China search, extract."""
    return [
        build_tavily_search(api_key=api_key),
        build_tavily_search_china(api_key=api_key),
        build_tavily_extract(api_key=api_key),
    ]
