from langchain_tavily import TavilyExtract, TavilySearch

from app.services.tavily_tools import (
    DEFAULT_MAX_RESULTS,
    build_quiz_research_tools,
    build_tavily_extract,
    build_tavily_search,
    build_tavily_search_china,
)


def test_build_global_search_defaults():
    tool = build_tavily_search(api_key="tvly-test")
    assert isinstance(tool, TavilySearch)
    assert tool.name == "tavily_search"
    assert tool.max_results == DEFAULT_MAX_RESULTS
    assert tool.topic == "general"
    assert tool.include_raw_content is False
    assert tool.country is None


def test_build_china_search_sets_country_only_on_china_tool():
    global_tool = build_tavily_search(api_key="tvly-test")
    china_tool = build_tavily_search_china(api_key="tvly-test")
    assert isinstance(china_tool, TavilySearch)
    assert china_tool.name == "tavily_search_china"
    assert china_tool.country == "china"
    assert china_tool.max_results == global_tool.max_results
    assert china_tool.include_raw_content is False
    assert global_tool.country is None


def test_build_extract_defaults():
    tool = build_tavily_extract(api_key="tvly-test")
    assert isinstance(tool, TavilyExtract)
    assert tool.name == "tavily_extract"
    assert tool.extract_depth == "basic"


def test_build_quiz_research_tools_order_and_types():
    tools = build_quiz_research_tools(api_key="tvly-test")
    assert len(tools) == 3
    assert [t.name for t in tools] == [
        "tavily_search",
        "tavily_search_china",
        "tavily_extract",
    ]
    assert isinstance(tools[0], TavilySearch)
    assert isinstance(tools[1], TavilySearch)
    assert isinstance(tools[2], TavilyExtract)
    # No custom per-call wrapper layer: tools are official langchain_tavily classes.
    assert all(t.__class__.__module__.startswith("langchain_tavily") for t in tools)
