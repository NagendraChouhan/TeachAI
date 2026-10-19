"""Router accuracy: does the agent pick the right action for each labelled teacher message?
Run from backend/:  python -m evaluation.run_router
Needs the Groq key (about 40 small calls)."""
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from app.graph import classify
from .common import RESULTS, with_retry

cases = json.loads((Path(__file__).parent / "router_cases.json").read_text())
rows, t0 = [], time.time()

for n, c in enumerate(cases, 1):
    history = []
    for k, h in enumerate(c.get("history", [])):
        history.append(HumanMessage(content=h) if k % 2 == 0 else AIMessage(content=h))
    history.append(HumanMessage(content=c["msg"]))
    try:
        plan = with_retry(lambda: classify(history))
        got, got_fk, err = plan.intent, plan.file_kind, None
    except Exception as e:
        got, got_fk, err = "ERROR", None, f"{type(e).__name__}: {e}"[:120]
    ok = got == c["intent"]
    fk_ok = None
    if c["intent"] == "email" and "file_kind" in c:
        fk_ok = got_fk == c["file_kind"]
    rows.append({**c, "got": got, "got_file_kind": got_fk, "intent_ok": ok, "file_kind_ok": fk_ok, "error": err})
    print(f"[{n:2}/{len(cases)}] {'OK ' if ok else 'BAD'} expected={c['intent']:<8} got={got:<8} | {c['msg'][:60]}", flush=True)
    time.sleep(0.5)

total = len(rows)
correct = sum(r["intent_ok"] for r in rows)
emails = [r for r in rows if r["file_kind_ok"] is not None]
fk_correct = sum(r["file_kind_ok"] for r in emails)
per = defaultdict(lambda: [0, 0])
for r in rows:
    per[r["intent"]][1] += 1
    per[r["intent"]][0] += r["intent_ok"]
confusions = Counter((r["intent"], r["got"]) for r in rows if not r["intent_ok"])

summary = {"total": total, "correct": correct, "accuracy": round(correct / total, 3),
           "email_attachment_correct": f"{fk_correct}/{len(emails)}",
           "per_intent": {k: f"{v[0]}/{v[1]}" for k, v in per.items()},
           "seconds": round(time.time() - t0)}
(RESULTS / "router_results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))

md = [f"# Router accuracy", "", f"- **Overall: {correct}/{total} = {correct / total:.0%}**",
      f"- Email attachment choice (none/ppt/reading/quiz): **{fk_correct}/{len(emails)}**", "",
      "| Intent | Correct |", "|---|---|"] + [f"| {k} | {v[0]}/{v[1]} |" for k, v in sorted(per.items())]
if confusions:
    md += ["", "## Mistakes", "", "| Expected | Got | Message |", "|---|---|---|"]
    md += [f"| {r['intent']} | {r['got']} | {r['msg']} |" for r in rows if not r["intent_ok"]]
(RESULTS / "router_report.md").write_text("\n".join(md) + "\n")
print("\n" + "\n".join(md))
