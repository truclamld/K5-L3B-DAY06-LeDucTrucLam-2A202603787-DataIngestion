"""Evidence-based retrieval metrics with query-level audit traces."""
import re
import unicodedata
from typing import Any


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", value).strip()


def _gold_options(question: dict[str, Any]) -> list[dict[str, Any]]:
    alternatives = question.get("gold_evidence") or question.get("alternatives") or []
    options = [{"source": question.get("gold_source_id"), "page": question.get("gold_page"),
                "quote": question.get("evidence_quote")}]
    for item in alternatives:
        if isinstance(item, dict):
            options.append({"source": item.get("gold_source_id", item.get("source", question.get("gold_source_id"))),
                            "page": item.get("gold_page", item.get("page")),
                            "quote": item.get("evidence_quote", item.get("quote"))})
    for quote in question.get("evidence_quotes", []):
        options.append({"source": question.get("gold_source_id"), "page": question.get("gold_page"), "quote": quote})
    if question.get("evidence_quote_2"):
        options.append({"source": question.get("gold_source_id"), "page": question.get("gold_page"), "quote": question["evidence_quote_2"]})
    return options


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """TODO: check source/page and enough gold evidence; keep hit@1 and hit@3 trace.

    Accept any documented alternative gold evidence. Do not infer human grounding
    or chunk coherence labels from exact string match.
    """
    options = _gold_options(question)
    def matches(hit: dict[str, Any], option: dict[str, Any]) -> bool:
        source = hit.get("source") == option["source"]
        page = str(hit.get("page")) == str(option["page"])
        quote = option.get("quote")
        has_quote = not quote or _norm(quote) in _norm(hit.get("text", ""))
        return source and page and has_quote
    trace_hits = []
    for rank, hit in enumerate(hits[:3], start=1):
        trace_hits.append({**hit, "rank": rank,
                           "gold_match": any(matches(hit, option) for option in options)})
    first = bool(trace_hits and trace_hits[0]["gold_match"])
    return {"id": question.get("id"), "split": question.get("split"), "strategy": question.get("strategy"),
            "question": question.get("question"), "expected_answer": question.get("expected_answer"),
            "gold": options, "filter": question.get("filter"), "hit_at_1": int(first),
            "evidence_hit_at_3": int(any(h["gold_match"] for h in trace_hits)), "hits": trace_hits}


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """TODO: aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    groups: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
    for trace in traces:
        groups.setdefault((trace.get("strategy"), trace.get("split")), []).append(trace)
    return {f"{strategy}/{split}": {
        "strategy": strategy, "split": split, "questions": len(rows),
        "hit_at_1": sum(r["hit_at_1"] for r in rows) / len(rows),
        "evidence_hit_at_3": sum(r["evidence_hit_at_3"] for r in rows) / len(rows),
    } for (strategy, split), rows in sorted(groups.items(), key=lambda pair: (str(pair[0][0]), str(pair[0][1])))}
