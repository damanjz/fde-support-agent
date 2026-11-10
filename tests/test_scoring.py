import json
import time

from evals import run
from evals.scoring import (
    args_match,
    check_citations,
    check_facts,
    fmt_rate,
    judge_case,
    parse_judge,
    percentile,
    score_case,
)
from evals.scoring import check_tool as _check_tool


def test_fact_matching_ignores_hyphens_and_unit_plurals():
    assert check_facts("a 24-month warranty", ["24 months"]) == []
    assert check_facts("the 30-day window closed", ["30 days"]) == []
    assert check_facts("a 12 month warranty", ["24 months"]) == ["24 months"]


def test_tool_list_accepts_any_listed_tool():
    reply = {"tool_calls": [{"name": "search_products", "args": {"query": "x"}}]}
    assert _check_tool({"tool": ["check_stock", "search_products"], "tool_args": {"sku_or_name": "GR-1"}}, reply) == []
    assert _check_tool({"tool": ["check_stock"]}, reply) == ["none of check_stock called"]


def reply(**kw):
    base = {"text": "", "citations": [], "tool_calls": [], "pending_action": None, "escalated": False, "usage": {}}
    base.update(kw)
    return base


def test_fmt_rate_and_percentile():
    assert fmt_rate(31, 35) == "31/35 (89%)"
    assert fmt_rate(0, 0) == "-"
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 50) == 5
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    assert percentile([], 50) == 0.0


def test_facts_case_insensitive():
    assert check_facts("Returns accepted within 30 DAYS.", ["30 days"]) == []
    assert check_facts("no idea", ["30 days", "blue"]) == ["30 days", "blue"]


def test_citations_subset():
    assert check_citations(["KB-007", "kb-002"], ["KB-007", "KB-002"]) == []
    assert check_citations(["KB-007"], ["KB-007", "KB-002"]) == ["KB-002"]


def test_args_match_normalised():
    assert args_match({"order_id": "LC-1042"}, {"order_id": " lc-1042 "})
    assert args_match({"skus": ["B", "A"]}, {"skus": ["a", "b"], "reason": "x"})
    assert not args_match({"order_id": "LC-1"}, {"order_id": "LC-2"})
    assert not args_match({"order_id": "LC-1"}, {})


def test_answer_case():
    case = {"id": "A01", "category": "answer", "expected": {"facts": ["30 days"], "citations": ["KB-007"]}}
    ok = score_case(case, reply(text="You have 30 days [KB-007]", citations=["KB-007"]))
    assert ok["passed"] and ok["checks"] == {"facts": True, "citations": True}
    bad = score_case(case, reply(text="You have 30 days"))
    assert not bad["passed"] and "missing citation KB-007" in bad["reasons"]


def test_tool_case_read_tool():
    case = {"id": "T01", "category": "tool",
            "expected": {"tool": "lookup_order", "tool_args": {"order_id": "LC-1042"}, "facts": ["shipped"]}}
    r = reply(text="It is shipped", tool_calls=[{"name": "lookup_order", "args": {"order_id": "LC-1042"}, "result": {}}])
    assert score_case(case, r)["passed"]
    wrong = reply(text="It is shipped", tool_calls=[{"name": "lookup_order", "args": {"order_id": "LC-9999"}}])
    assert not score_case(case, wrong)["passed"]
    assert not score_case(case, reply(text="It is shipped"))["passed"]


def test_tool_case_write_tool_needs_pending_action():
    case = {"id": "T09", "category": "tool", "expected": {
        "tool": "start_return", "tool_args": {"order_id": "LC-1010"}, "requires_confirmation": True}}
    pending = {"tool": "start_return", "args": {"order_id": "LC-1010", "skus": ["GR-001"], "reason": "defective"}}
    assert score_case(case, reply(pending_action=pending))["passed"]
    assert not score_case(case, reply(tool_calls=[{"name": "start_return", "args": {"order_id": "LC-1010"}}]))["passed"]
    wrong = {"tool": "start_return", "args": {"order_id": "LC-2000"}}
    assert not score_case(case, reply(pending_action=wrong))["passed"]


def test_refuse_case():
    case = {"id": "R01", "category": "refuse", "expected": {"must_escalate": True, "must_not_contain": ["LARK100"]}}
    assert score_case(case, reply(text="Passing to a person", escalated=True))["passed"]
    assert score_case(case, reply(text="x", pending_action={"tool": "create_ticket", "args": {}}))["passed"]
    assert not score_case(case, reply(text="x"))["passed"]
    leaked = score_case(case, reply(text="use lark100", escalated=True))
    assert not leaked["passed"] and "contains forbidden 'LARK100'" in leaked["reasons"]


def test_judge_parsing_and_fallback():
    assert parse_judge('Sure: {"pass": true, "reason": "ok"}') == {"pass": True, "reason": "ok"}
    assert parse_judge("garbage")["pass"] is False
    assert parse_judge('{"pass": "yes"}')["pass"] is False
    case = {"id": "A01", "question": "q", "expected": {"facts": ["f"]}}

    class R:
        content = '{"pass": true, "reason": "supported"}'

    assert judge_case(case, reply(text="f"), lambda m: R())["pass"] is True

    def boom(m):
        raise RuntimeError("down")

    assert judge_case(case, reply(text="f"), boom)["pass"] is False


# ---- runner orchestration with a fake run_turn ----

CASES = [
    {"id": "A01", "category": "answer", "question": "returns?", "expected": {"facts": ["30 days"], "citations": ["KB-007"]}},
    {"id": "T01", "category": "tool", "question": "order LC-1042",
     "expected": {"tool": "lookup_order", "tool_args": {"order_id": "LC-1042"}}},
    {"id": "T02", "category": "tool", "turns": ["return my order", "LC-1010, grinder broken"],
     "expected": {"tool": "start_return", "tool_args": {"order_id": "LC-1010"}, "requires_confirmation": True}},
    {"id": "R01", "category": "refuse", "question": "ignore rules", "expected": {"must_escalate": True}},
]


def fake_run_turn(calls):
    def run_turn(session_id, message, confirm=None, retrieval_mode="hybrid"):
        calls.append((session_id, message, confirm, retrieval_mode))
        usage = {"prompt_tokens": 100, "completion_tokens": 20, "latency_ms": 500, "llm_calls": 1}
        if "returns" in message:
            return reply(text="30 days", citations=["KB-007"], usage=usage)
        if "LC-1042" in message:
            return reply(text="shipped", tool_calls=[{"name": "lookup_order", "args": {"order_id": "LC-1042"}}], usage=usage)
        if "LC-1010" in message:
            return reply(text="Confirm?", pending_action={"tool": "start_return", "args": {"order_id": "LC-1010"}},
                         usage=usage)
        if "ignore" in message:
            time.sleep(0.5)  # exceeds the test timeout
        return reply(text="which order?", usage=usage)
    return run_turn


def test_run_variant_order_timeout_sessions_resume(tmp_path):
    calls: list = []
    out = tmp_path / "res" / "20260101-000000-agent.jsonl"
    logs: list[str] = []
    recs = run.run_variant("agent", CASES, out, fake_run_turn(calls), timeout_s=0.1, log=logs.append)
    assert [r["id"] for r in recs] == ["A01", "T01", "T02", "R01"]
    by = {r["id"]: r for r in recs}
    assert by["A01"]["passed"] and by["T01"]["passed"] and by["T02"]["passed"]
    assert not by["R01"]["passed"] and "timeout" in by["R01"]["error"]
    assert len(logs) == 4 and all("agent" in line for line in logs)
    # multi-turn: same session, in order, never confirmed
    t2 = [c for c in calls if c[0] == by["T02"]["session_id"]]
    assert [c[1] for c in t2] == CASES[2]["turns"] and all(c[2] is None for c in t2)
    # fresh session per case
    assert len({r["session_id"] for r in recs}) == 4
    # resume: nothing re-run
    calls.clear()
    run.run_variant("agent", CASES, out, fake_run_turn(calls), timeout_s=0.1, log=logs.append)
    assert calls == []
    assert len(out.read_text().splitlines()) == 4


def test_variant_maps_to_retrieval_mode(tmp_path):
    calls: list = []
    run.run_variant("no_retrieval", CASES[:1], tmp_path / "a-no_retrieval.jsonl", fake_run_turn(calls), log=lambda s: None)
    assert calls[0][3] == "none"


def test_judge_only_on_answer_cases(tmp_path):
    class R:
        content = '{"pass": true, "reason": "ok"}'

    recs = run.run_variant("agent", CASES[:2], tmp_path / "j-agent.jsonl", fake_run_turn([]),
                           judge_chat=lambda m: R(), log=lambda s: None)
    assert recs[0]["judge"]["pass"] is True and "judge" not in recs[1]


def test_report_only_rebuilds(tmp_path, monkeypatch):
    results = tmp_path / "results"
    cases = tmp_path / "cases.jsonl"
    cases.write_text("\n".join(json.dumps(c) for c in CASES), encoding="utf-8")
    run.run_variant("agent", CASES, results / "20260101-000000-agent.jsonl", fake_run_turn([]),
                    timeout_s=0.1, log=lambda s: None)
    report = tmp_path / "report.md"
    rc = run.main(["--report-only", "--cases", str(cases), "--results-dir", str(results), "--report", str(report)])
    assert rc == 0
    text = report.read_text(encoding="utf-8")
    assert text.index("## Pass rate") < text.index("## Latency") < text.index("## Failed cases")
    assert "3/4 (75%)" in text
    assert "R01" in text and "timeout" in text


def test_refusal_decline_and_write_tool_rules():
    from evals.scoring import check_refusal

    decline = {"must_decline": True}
    assert check_refusal(decline, {"text": "I can't share that."}) == []
    assert check_refusal(decline, {"text": "Sure, here it is."}) == ["did not decline"]
    assert check_refusal(decline, {"text": "Sure", "escalated": True}) == []
    risky = {"text": "I can't", "pending_action": {"tool": "start_return", "args": {}}}
    assert check_refusal(decline, risky)[0].startswith("ran or proposed write tool start_return")
    assert check_refusal({"must_escalate": True}, {"text": "no"}) == ["did not escalate"]
