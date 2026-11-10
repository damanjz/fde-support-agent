# Larkfield support agent

A customer-support agent for a fictional Indian coffee-gear brand, Larkfield Coffee Co. It answers from the help centre with citations, looks up orders and stock, starts returns and raises tickets only after the customer confirms, and hands off to a person when unsure. Runs fully local: FastAPI, Postgres + pgvector, a 27B model through Ollama.

The company and all data are synthetic. The engineering, the evaluation and the numbers are real.

## Results (eval run 5, 2026-11-10, `evals/report.md`)
60 cases: 35 answer questions, 15 tool tasks, 10 that must refuse or escalate (prompt injection, another customer's data, outdated-policy trap, fake admin). Pass = every exact check passed.

| Variant | Answer | Tool | Refuse | Overall | LLM judge (answers) |
|---|---|---|---|---|---|
| Agent (hybrid retrieval + tools + guardrails) | 32/35 (91%) | 14/15 (93%) | 10/10 (100%) | **56/60 (93%)** | 35/35 (100%) |
| Keyword-only retrieval | 28/35 (80%) | 14/15 (93%) | 10/10 (100%) | 52/60 (87%) | 32/35 (91%) |
| No retrieval | 0/35 (0%) | 14/15 (93%) | 8/10 (80%) | 22/60 (37%) | 10/35 (29%) |

| Agent | p50 | p95 | Prompt tokens / query | Cost / query |
|---|---|---|---|---|
| Local fusion27b:iq3 on one RTX 5080 | 14.8 s | 26.5 s | 4,147 | INR 0.00 |

- Run 1 to run 5, agent: 77% to 93%. Every change between runs is listed in `docs/engagement.md`.
- 3 of the 4 remaining agent failures are correct answers the exact scorer misses; a hand-check of 15 answers agreed with the LLM judge on 15/15 (`evals/judge-handcheck.md`).

## How it was tested beyond the eval
40 unscripted conversations with simulated customers (angry, anxious, red-team, messy Hinglish) found 76 issues, 2 critical, which were fixed at the root cause. Transcripts and findings: `evals/convos/`. Write-up: `docs/engagement.md`.

## What it does
| Capability | How |
|---|---|
| Grounded answers | Hybrid retrieval (Postgres full-text + pgvector, reciprocal rank fusion), expanded to whole top articles; every policy claim cited `[KB-xxx]`; citations to unretrieved articles are stripped |
| Tools | `lookup_order` (with computed date facts), `check_stock`, `search_products`, `start_return` (per-unit, refund estimate, dry-run against policy before asking), `create_ticket` |
| Human in the loop | Write tools wait for Confirm or Cancel (buttons or typed yes/no, Hinglish included); the card survives side questions |
| Honesty checks | A reply that claims an action without a tool call is retried; invented ticket numbers are blocked |
| Guardrails | PII masking in tool output and logs; injection lines removed from retrieved text; authority claims declined; codes not found in real data are blocked |
| Channels | REST API, local chat page, Slack bot (Socket Mode) |

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

## Layout
| Path | What |
|---|---|
| `app/` | agent loop, retrieval, tools, guardrails, LLM client, API |
| `data/` | 40 help articles, 50 products, 200 orders, 30 past tickets, generator and validator |
| `evals/` | 60 cases, runner, scoring, reports per run, simulated conversations |
| `docs/` | spec, build contract, runbook, engagement write-up |

## Known limits
- Identity is not verified: any order id typed in chat can be looked up (contact details are masked).
- The model sometimes cites the right rule from a second article that also states it, and once misread a date from a tool result.
- One local GPU: about 15 s per reply, one conversation at a time.

## How this was built

Built with Claude Code as a pair programmer. Scope, design decisions and verification are mine. Larkfield Coffee Co. is a fictional customer; all data is synthetic. MIT licensed (see `LICENSE`).
