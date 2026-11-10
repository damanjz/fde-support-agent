# Larkfield support agent

A customer-support agent for a fictional Indian coffee-gear brand, Larkfield Coffee Co. It answers from the help centre with citations, looks up orders and stock, starts returns and raises tickets only after the customer confirms, and hands off to a person when unsure. Runs fully local: FastAPI, Postgres + pgvector, a 27B model through Ollama.

[![Larkfield support agent demo reel](docs/media/reel.gif)](docs/media/reel.mp4)
<sub>29-second reel. Click for the full video.</sub>

| Overall pass rate | Judge pass, answers | Median reply, cost per query |
|---|---|---|
| **53/60 (88%)** on the 60-case eval, against 83% for keyword-only retrieval and 38% for no retrieval | **35/35 (100%)** on the 35 answer cases, hand-checked on 15 of them | **7.3 s, INR 0.00** on one local RTX 5080 |

Sources: `evals/report.md` (eval run 6, 2026-11-10) and `evals/judge-handcheck.md`. The company and all data are synthetic. The engineering, the evaluation and the numbers are real.

## The problem
Larkfield wants a support agent that answers from its help centre, looks up orders and stock, and starts returns and tickets, with no recurring cost. It must not invent policy, dates or order data, and must not act without the customer's confirmation. Details: `docs/engagement.md`.

## Architecture
![Architecture: customer, input guardrails, agent loop with retrieval and tools, output checks, reply, Postgres](docs/diagrams/architecture.svg)

- **Hybrid retrieval, whole articles.** Postgres full-text and pgvector are fused by reciprocal rank fusion, then expanded to whole top articles so a policy is never cut off mid-rule. Every policy claim is cited `[KB-xxx]`, and citations to articles that were not retrieved are stripped.
- **Date arithmetic lives in code.** `lookup_order` returns computed facts (days since delivery, return window, business days since dispatch). The model was caught getting this wrong and holding the line under pressure.
- **Writes need a click.** `start_return` (per-unit, refund estimate, dry run against policy before asking) and `create_ticket` wait for Confirm or Cancel, by button or typed yes/no, Hinglish included. The card survives side questions.
- **Honesty checks on output.** A reply that claims an action without a tool call is retried once. Invented ticket numbers and codes not found in real data are blocked.
- **Guardrails on input.** PII is masked in tool output and logs, injection lines are removed from retrieved text, and authority claims such as "ADMIN OVERRIDE" are declined.
- **Channels.** REST API, a local chat page and a Slack bot (Socket Mode).

## One request, traced
![Trace of one return request through API, agent, retrieval, tools and Postgres](docs/diagrams/trace.svg)

Larkfield's customers ask the same things all day: where is my order, can I return this, is it in stock, what is the policy. They write in English and Hinglish, with typos, sometimes angry. The shop wants answers grounded in its own help centre, real actions on orders that never happen without the customer's clear yes, a hand-off to a person when unsure, and no recurring cost: everything runs locally.

## Results
Eval run 6, 2026-11-10, `evals/report.md` (run 5: `evals/report-run5-2026-11-10.md`). 60 cases: 35 answer questions, 15 tool tasks, 10 that must refuse or escalate (prompt injection, another customer's data, outdated-policy trap, fake admin). Pass = every exact check passed.

| Variant | Answer | Tool | Refuse | Overall | LLM judge (answers) |
|---|---|---|---|---|---|
| Agent (hybrid retrieval + tools + guardrails) | 30/35 (86%) | 13/15 (87%) | 10/10 (100%) | **53/60 (88%)** | 35/35 (100%) |
| Keyword-only retrieval | 27/35 (77%) | 13/15 (87%) | 10/10 (100%) | 50/60 (83%) | 32/35 (91%) |
| No retrieval | 0/35 (0%) | 15/15 (100%) | 8/10 (80%) | 23/60 (38%) | 10/35 (29%) |

| Agent | p50 | p95 | Prompt tokens / query | Cost / query |
|---|---|---|---|---|
| Local fusion27b:iq3 on one RTX 5080 | 7.3 s | 11.0 s | 4,518 | INR 0.00 |

- Run 1 to run 5, agent: 77% to 93%. Run 6 (2026-11-10) added a computed 48-hour not-received deadline after a live voice test caught the agent offering an expired option: 88%. The 3-case drop is inside the noise measured in project 5 (4 of 60 cases flip between identical runs), and all 3 new failures are correct answers worded differently from the exact checks (A16 "can no longer be cancelled", A28 "every 2 or 4 weeks", T11 states the closed return date instead of "30 days").
- All 5 failed answer cases pass the LLM judge. A hand-check of 15 answers agreed with the judge on 15/15 (`evals/judge-handcheck.md`). Every change between runs is listed in `docs/engagement.md`.
- Latency: 7.3 s p50 in run 6 against 14.8 s in run 5 on the same hardware. Other jobs on the one GPU vary between runs, so read latency as indicative.

## How it was tested
- **Two baselines**, same 60 cases: keyword-only retrieval, and no retrieval. The run 3 and run 5 fixes also help the keyword variant, so the agent-vs-keyword gap narrowed from 10 points to 6 (run 5) and 5 (run 6). Both are reported as measured.
- **Scoring rules** were changed only before a run, applied to every variant and noted in the case `notes`. No case was edited after seeing its result in the same run.
- **40 unscripted conversations** with simulated customers (angry, anxious, red-team, messy Hinglish) found 76 issues, 2 critical, which were fixed at the root cause. Transcripts and findings: `evals/convos/`.
- **Adversarial cases** in the eval: prompt injection planted in a help article, another customer's data, an outdated return policy that contradicts the current one, a fake admin override.
- **What the numbers do not claim:** the exact scorer fails some correct answers, so the judge column is the better read for answers. The judge is a model too, which is why 15 answers were checked by hand. The 7 agent failures of run 6 are listed in `evals/report.md`.

## Run it
```bash
docker compose up -d db
python -m app.ingest
uvicorn app.main:app --port 8000
```
Open http://localhost:8000. Requires Ollama with `fusion27b:iq3` and `nomic-embed-text`. Details: `docs/runbook.md`.

```bash
python -m ruff check .
python -m pytest -q
python -m evals.run --variant all --judge
```

## Repository layout
| Path | What |
|---|---|
| `app/` | agent loop, retrieval, tools, guardrails, LLM client, API |
| `data/` | 40 help articles, 50 products, 200 orders, 30 past tickets, generator and validator |
| `evals/` | 60 cases, runner, scoring, reports per run, simulated conversations |
| `docs/` | spec, build contract, runbook, engagement write-up, diagrams, reel |

## Known limits
- Identity is not verified: any order id typed in chat can be looked up (contact details are masked).
- The model sometimes cites the right rule from a second article that also states it, and once misread a date from a tool result.
- One local GPU: about 15 s per reply, one conversation at a time.

## How this was built

Built with Claude Code as a pair programmer. Scope, design decisions and verification are mine. Larkfield Coffee Co. is a fictional customer; all data is synthetic. MIT licensed (see `LICENSE`).

<!-- signature -->
<p align="center"><img src="docs/media/signature.gif" width="200" alt="A cat typing on a laptop"><br><sub>Signature GIF: <a href="https://commons.wikimedia.org/wiki/File:Cat_Laptop_-_Idil_Keysan_-_Wikimedia_Giphy_stickers_2019.gif">A cat typing on a laptop</a> by Idil Keysan for the Wikimedia Foundation, CC BY-SA 4.0, via Wikimedia Commons.</sub></p>
