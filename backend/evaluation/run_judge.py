"""LLM-as-judge: generate answers / PPT / reading material / quiz / emails with the real agent, then have a
DIFFERENT model (JUDGE_MODEL, default qwen/qwen3.8-27b) score each one against a rubric (1-5), plus plain
programmatic checks (slide count, question count, attachment...). Emails are only drafted, never sent.
Run from backend/:  python -m evaluation.run_judge      (takes several minutes; uses the Groq key)"""
import json
import os
import time
from pathlib import Path
from statistics import mean

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from app.context import gather
from app.graph import checkpointer, graph
from app.store import get_class
from .common import RESULTS, with_retry

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "qwen/qwen3.8-27b")
CLASS = "eval-class"

RUBRICS = {
    "qa": ["relevance", "faithfulness_to_sources", "accuracy", "clarity"],
    "ppt": ["topic_coverage", "clarity_for_students", "logical_flow", "conciseness"],
    "reading": ["topic_coverage", "explanation_quality", "structure", "student_friendliness"],
    "quiz": ["question_quality", "answer_correctness", "coverage_and_variety", "clarity"],
    "email": ["follows_teacher_request", "no_invented_facts", "tone_and_clarity", "appropriate_length"],
}
EXPLAIN = {
    "relevance": "answers exactly what was asked", "faithfulness_to_sources": "claims are supported by the source material (not invented)",
    "accuracy": "factually correct", "clarity": "easy to understand", "topic_coverage": "covers the requested topic well",
    "clarity_for_students": "wording suits school students", "logical_flow": "ideas follow a sensible order",
    "conciseness": "short, not cluttered", "explanation_quality": "explains concepts well with examples",
    "structure": "well organised with headings and a clear flow", "student_friendliness": "engaging and simple for students",
    "question_quality": "questions are clear, unambiguous and test understanding", "answer_correctness": "the given answers are correct",
    "coverage_and_variety": "covers the topic broadly with a good mix of question types",
    "follows_teacher_request": "says what the teacher asked, nothing else", "no_invented_facts": "adds no facts, times, dates or links the teacher did not give",
    "tone_and_clarity": "polite, professional, clear", "appropriate_length": "short and to the point",
}


class Crit(BaseModel):
    name: str
    score: int = Field(description="1 (poor) to 5 (excellent)")
    reason: str = Field(description="one short sentence of evidence")


class Verdict(BaseModel):
    scores: list[Crit]


judge = ChatGroq(model=JUDGE_MODEL, temperature=0).with_structured_output(Verdict)


def judge_it(kind: str, request: str, material: str) -> dict:
    names = RUBRICS[kind]
    rubric = "\n".join(f"- {n}: {EXPLAIN[n]}" for n in names)
    msgs = [SystemMessage(content="You are a strict, fair evaluator of teaching material produced by an AI assistant. "
                          "Score each criterion from 1 to 5 (5 = flawless, 3 = acceptable, 1 = bad). Base every score only on "
                          "the text shown. Be critical: do not give 5 unless it is genuinely excellent. "
                          f"Return exactly these criteria, using these exact names:\n{rubric}"),
            HumanMessage(content=f"TEACHER REQUEST:\n{request}\n\n{material[:7000]}")]
    v = with_retry(lambda: judge.invoke(msgs))
    got = {c.name: c for c in v.scores}
    return {n: {"score": max(1, min(5, got[n].score)), "reason": got[n].reason} for n in names if n in got}


def run_case(i: int, case: dict) -> dict:
    cfg = {"configurable": {"thread_id": f"eval-{i}"}}
    t0 = time.time()
    out = with_retry(lambda: graph.invoke({"messages": [HumanMessage(content=case["msg"])]}, cfg))
    secs = round(time.time() - t0, 1)
    st = graph.get_state(cfg)
    routed = st.values["plan"]["intent"]
    kind, checks = case["type"], {}
    exp = case.get("expect", {})
    if kind == "qa":
        reply = out["messages"][-1].content
        src = gather([case["msg"]])[0]
        material = f"SOURCE MATERIAL (from the teacher's books / web):\n{src}\n\nASSISTANT ANSWER:\n{reply}"
    elif kind == "ppt":
        rec = get_class(CLASS)["ppt"]
        material = "SLIDES:\n" + "\n".join(f"{n}. {s['title']}\n   " + "\n   ".join(f"- {b}" for b in s["bullets"])
                                           for n, s in enumerate(rec["slides"], 1))
        checks["slide_count"] = len(rec["slides"]) == exp["slides"]
    elif kind == "reading":
        material = "READING MATERIAL:\n" + get_class(CLASS)["reading"]["text"]
    elif kind == "quiz":
        qs = get_class(CLASS)["quiz"]["questions"]
        material = "QUESTION PAPER (with answer key):\n" + "\n".join(
            f"{n}. [{q['type']}, {q['marks']} marks] {q['question']}\n" + "".join(f"   {l}) {o}\n" for l, o in zip('ABCD', q['options']))
            + f"   ANSWER: {q['answer']}" for n, q in enumerate(qs, 1))
        checks["question_count"] = len(qs) == exp["questions"]
        checks["mcq_have_4_options"] = all(len(q["options"]) == 4 for q in qs if q["type"] == "mcq")
        checks["all_have_answers"] = all(q["answer"].strip() for q in qs)
    elif kind == "email":
        d = st.values.get("draft") or {}
        paused = bool(st.next)  # paused at the approval step = nothing was sent
        material = (f"EMAIL DRAFT:\nTo: {', '.join(d.get('to', []))}\nSubject: {d.get('subject')}\n"
                    f"Attachment: {d.get('attachment') or 'none'}\n\n{d.get('body')}")
        want = exp["attachment"]
        checks["paused_for_approval"] = paused
        checks["attachment_correct"] = (d.get("attachment") is None) if want is None else bool(d.get("attachment")) and want in d["attachment"]
    checks["routed_to_" + kind] = routed == kind or (kind == "email" and routed == "email")
    scores = judge_it(kind, case["msg"], material)
    return {"id": case["id"], "type": kind, "request": case["msg"], "seconds": secs, "checks": checks, "scores": scores,
            "avg": round(mean(v["score"] for v in scores.values()), 2) if scores else None}


cases = json.loads((Path(__file__).parent / "judge_cases.json").read_text())
rows = []
for i, c in enumerate(cases):
    print(f"[{i + 1}/{len(cases)}] {c['id']}: {c['msg'][:70]}", flush=True)
    try:
        r = run_case(i, c)
        print(f"     avg {r['avg']}/5  checks {r['checks']}  ({r['seconds']}s)", flush=True)
    except Exception as e:
        r = {"id": c["id"], "type": c["type"], "request": c["msg"], "error": f"{type(e).__name__}: {e}"[:300], "scores": {}, "checks": {}, "avg": None}
        print("     ERROR", r["error"], flush=True)
    rows.append(r)
    try:
        checkpointer.delete_thread(f"eval-{i}")
    except Exception:
        pass

ok = [r for r in rows if r["avg"] is not None]
by_type = {}
for r in ok:
    by_type.setdefault(r["type"], []).append(r)
all_scores = [v["score"] for r in ok for v in r["scores"].values()]
summary = {"judge_model": JUDGE_MODEL, "generator_model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
           "cases": len(rows), "judged": len(ok), "errors": len(rows) - len(ok),
           "overall_avg_of_5": round(mean(all_scores), 2) if all_scores else None,
           "criteria_scored_4_or_5": f"{round(100 * sum(s >= 4 for s in all_scores) / len(all_scores))}%" if all_scores else None,
           "programmatic_checks_passed": f"{sum(v for r in ok for v in r['checks'].values())}/{sum(len(r['checks']) for r in ok)}",
           "by_type": {t: round(mean(r["avg"] for r in rs), 2) for t, rs in by_type.items()}}
(RESULTS / "judge_results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))

md = ["# LLM-as-judge results", "",
      f"Generator: `{summary['generator_model']}`  |  Judge: `{JUDGE_MODEL}` (different model)  |  Scale 1-5", "",
      f"- **Overall average: {summary['overall_avg_of_5']}/5**  ({summary['judged']} of {summary['cases']} cases judged)",
      f"- Criteria scored 4 or 5: **{summary['criteria_scored_4_or_5']}**",
      f"- Programmatic checks passed: **{summary['programmatic_checks_passed']}**", "",
      "| Output type | Cases | Avg score (1-5) |", "|---|---|---|"]
md += [f"| {t} | {len(rs)} | {round(mean(r['avg'] for r in rs), 2)} |" for t, rs in by_type.items()]
md += ["", "## Per case", "", "| Case | Request | Avg | Checks | Time |", "|---|---|---|---|---|"]
for r in rows:
    chk = ", ".join(f"{k}: {'pass' if v else 'FAIL'}" for k, v in r["checks"].items()) or r.get("error", "")
    md.append(f"| {r['id']} | {r['request'][:55]} | {r['avg']} | {chk} | {r.get('seconds', '')}s |")
md += ["", "## Judge's reasons (lowest score per case)", ""]
for r in ok:
    n, v = min(r["scores"].items(), key=lambda kv: kv[1]["score"])
    md.append(f"- **{r['id']}** lowest: {n} = {v['score']}: {v['reason']}")
(RESULTS / "judge_report.md").write_text("\n".join(md) + "\n")
print("\n" + "\n".join(md))
