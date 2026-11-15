"""Rule-based (and optional LLM) question extraction for drill mode."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

IMAGE_HINT = re.compile(
    r"(见图|如图|下图|上图|附图|图片|插图|图\s*\d|【图|!\[|\.png|\.jpg|\.jpeg|\.gif|\.webp)",
    re.I,
)
# Supports: 1. / 1、 / (1) / 第1题 / 2-1 / 2.1（教材章节题号）
QUESTION_START = re.compile(
    r"(?m)^\s*(?:"
    r"第?\s*\d+\s*[题\.、．]"
    r"|[（(]?\d+[）)][.、．]?"
    r"|\d+\s*[-−–—\.．]\s*\d+"
    r"|[一二三四五六七八九十]+[、．.]"
    r")\s*"
)
OPTION_LINE = re.compile(r"(?m)^\s*([A-Da-d])[\.．、\)]\s*(.+?)\s*$")
# Supports: 答案：B / 【答案】D / 正确答案: AB
ANSWER_LINE = re.compile(
    r"(?m)^\s*(?:【\s*答案\s*】|答案|正确答案)\s*[:：]?\s*"
    r"([A-Da-d]+|[对错√×对是非否]+)\s*$"
)
# Supports: 解析：… / 【解析】 / 【解析】正文
EXPLAIN_LINE = re.compile(
    r"(?m)^\s*(?:【\s*解析\s*】|解析|解答|说明)\s*[:：]?\s*(.*)$"
)
JUDGE_TRUE = {"对", "正确", "√", "是", "T", "TRUE", "对的"}
JUDGE_FALSE = {"错", "错误", "×", "否", "F", "FALSE", "错的"}


@dataclass
class ExtractedQuestion:
    qtype: str  # single | multi | judge
    stem: str
    options: list[str]
    answer_indices: list[int]
    explanation: str | None = None
    confidence: float = 0.0
    looks_like_image: bool = False


@dataclass
class SplitResult:
    questions: list[ExtractedQuestion] = field(default_factory=list)
    suggested_mode: str = "master"  # drill | master
    confidence: float = 0.0
    warning: str | None = None


def looks_like_image_question(text: str) -> bool:
    return bool(IMAGE_HINT.search(text or ""))


def suggest_mode_from_text(text: str) -> tuple[str, float]:
    """Return (mode, confidence) from lightweight signals."""
    body = (text or "").strip()
    if not body:
        return "master", 0.2
    option_hits = len(OPTION_LINE.findall(body))
    q_starts = len(QUESTION_START.findall(body))
    answer_hits = len(ANSWER_LINE.findall(body))
    score = option_hits * 1.5 + q_starts * 2.0 + answer_hits * 2.0
    density = score / max(len(body) / 800.0, 1.0)
    if q_starts >= 3 and option_hits >= 6:
        return "drill", min(0.95, 0.55 + density * 0.05)
    if q_starts >= 1 and option_hits >= 2 and answer_hits >= 1:
        return "drill", min(0.85, 0.45 + density * 0.05)
    return "master", 0.6


def _parse_answer_token(token: str, options: list[str]) -> list[int] | None:
    raw = (token or "").strip().upper()
    if not raw:
        return None
    if raw in {t.upper() for t in JUDGE_TRUE}:
        return [0]
    if raw in {t.upper() for t in JUDGE_FALSE}:
        return [1]
    letters = re.findall(r"[A-D]", raw)
    if not letters:
        return None
    indices: list[int] = []
    for ch in letters:
        idx = ord(ch) - ord("A")
        if 0 <= idx < len(options):
            indices.append(idx)
    return indices or None


def _split_blocks(text: str) -> list[str]:
    body = (text or "").replace("\r\n", "\n").strip()
    if not body:
        return []
    matches = list(QUESTION_START.finditer(body))
    if not matches:
        return [body] if OPTION_LINE.search(body) else []
    blocks: list[str] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[m.start() : end].strip()
        if chunk:
            blocks.append(chunk)
    return blocks


def _extract_one(block: str) -> ExtractedQuestion | None:
    image = looks_like_image_question(block)
    options = [(m.group(1).upper(), m.group(2).strip()) for m in OPTION_LINE.finditer(block)]
    option_texts = [t for _, t in options]
    ans_m = ANSWER_LINE.search(block)
    exp_m = EXPLAIN_LINE.search(block)
    explanation = (exp_m.group(1).strip() or None) if exp_m else None

    # stem: before first option
    first_opt = OPTION_LINE.search(block)
    stem_region = block[: first_opt.start()] if first_opt else block
    stem = QUESTION_START.sub("", stem_region, count=1).strip()
    stem = ANSWER_LINE.sub("", stem)
    stem = EXPLAIN_LINE.sub("", stem).strip()
    if not stem:
        return None

    if len(option_texts) >= 2:
        answers = _parse_answer_token(ans_m.group(1), option_texts) if ans_m else None
        if not answers:
            # no answer → still keep with low confidence single guess disabled
            return ExtractedQuestion(
                qtype="multi" if False else "single",
                stem=stem,
                options=option_texts,
                answer_indices=[],
                explanation=explanation,
                confidence=0.35,
                looks_like_image=image,
            )
        qtype = "multi" if len(answers) > 1 else "single"
        conf = 0.9 if not image else 0.4
        return ExtractedQuestion(
            qtype=qtype,
            stem=stem,
            options=option_texts,
            answer_indices=answers,
            explanation=explanation,
            confidence=conf,
            looks_like_image=image,
        )

    # judge: 对/错 style without A-D options
    if ans_m:
        token = ans_m.group(1).strip()
        if token.upper() in {t.upper() for t in JUDGE_TRUE} or token.upper() in {
            t.upper() for t in JUDGE_FALSE
        }:
            idx = 0 if token.upper() in {t.upper() for t in JUDGE_TRUE} else 1
            return ExtractedQuestion(
                qtype="judge",
                stem=stem,
                options=["正确", "错误"],
                answer_indices=[idx],
                explanation=explanation,
                confidence=0.8 if not image else 0.4,
                looks_like_image=image,
            )
    return None


def split_questions_with_llm_fallback(
    text: str,
    *,
    llm_splitter=None,
    min_confidence: float = 0.5,
) -> SplitResult:
    """Rule-first; optional llm_splitter(text)->list[ExtractedQuestion] when sparse."""
    result = split_questions_rule(text, min_confidence=min_confidence)
    if result.questions or llm_splitter is None:
        return result
    try:
        extra = llm_splitter(text) or []
    except Exception:  # noqa: BLE001
        return result
    usable = [
        q
        for q in extra
        if isinstance(q, ExtractedQuestion)
        and not q.looks_like_image
        and q.answer_indices
        and q.qtype in {"single", "multi", "judge"}
    ]
    if not usable:
        return SplitResult(
            questions=[],
            suggested_mode=result.suggested_mode,
            confidence=result.confidence,
            warning=(
                result.warning
                or "规则与模型均未能拆出可用文本题，请换规范题库或改学透"
            ),
        )
    return SplitResult(
        questions=usable,
        suggested_mode="drill",
        confidence=max(result.confidence, 0.55),
        warning=None,
    )


def split_questions_rule(text: str, *, min_confidence: float = 0.5) -> SplitResult:
    suggested, suggest_conf = suggest_mode_from_text(text)
    blocks = _split_blocks(text)
    extracted: list[ExtractedQuestion] = []
    for block in blocks:
        item = _extract_one(block)
        if item is None:
            continue
        if item.looks_like_image:
            continue
        if not item.answer_indices:
            continue
        if item.confidence < min_confidence:
            continue
        if item.qtype not in {"single", "multi", "judge"}:
            continue
        extracted.append(item)

    warning = None
    if suggested == "drill" and len(extracted) == 0:
        warning = "文档更像题库，但未能拆出可用文本题（可能含图片题或版式不规范）"
    elif suggested == "master" and len(extracted) >= 3:
        suggested = "drill"
        suggest_conf = max(suggest_conf, 0.7)
    conf = suggest_conf
    if extracted:
        conf = max(conf, sum(q.confidence for q in extracted) / len(extracted))
    return SplitResult(
        questions=extracted,
        suggested_mode=suggested,
        confidence=conf,
        warning=warning,
    )
