# Runbook: Larkfield support agent

For the person operating the agent after hand-off. Everything runs locally.

## Start
1. Start Ollama (host) and make sure the models exist: `ollama list` shows `fusion27b:iq3` and `nomic-embed-text`.
2. `docker compose up -d` (Postgres on port 5433, API on port 8000).
3. First time, or after help-centre changes: `python -m app.ingest` (reloads articles, products, orders, past tickets; about 40 s).
4. Check: `curl http://localhost:8000/health` returns `ok` for db and ollama. Chat page: http://localhost:8000.

## Stop
`docker compose stop`. Data stays in the `pgdata` volume. `docker compose down -v` deletes it.

## Update the help centre
1. Edit or add `data/articles/KB-xxx.md` (front matter: id, title, category, updated).
2. `python data/validate.py` must print OK.
3. `python -m app.ingest`.
4. `python -m evals.run --variant agent` and compare `evals/report.md` with the last run. Do not ship if any category drops.

## Switch the model
- Local (default): `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=...` in `.env`.
- Paid API: `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=...`, and set `PRICE_IN_PER_MTOK` / `PRICE_OUT_PER_MTOK` from the provider's price page so cost per query is reported.
- After any switch, rerun the eval before going live.

## Rotate keys
Edit `.env` (never committed), then `docker compose up -d api` to restart with the new values.

## Slack
Create a Slack app with Socket Mode, bot scopes `app_mentions:read`, `chat:write`, `im:history`; put `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in `.env`; run `python -m app.slack_bot`.

## When something goes wrong
| Symptom | Check | Fix |
|---|---|---|
| Every reply is the hand-off message | `/health`; `logs/requests.jsonl` for `output_flags` or errors; `logs/uvicorn.log` for `HTTPStatusError` | Start Ollama; if flags show a code, check the article for a planted code; a 500 from Ollama with "System message must be at the beginning" means code sent a second system message |
| `column "qty" does not exist` on returns | Database created before 2026-11-09 | `docker compose exec -T db psql -U larkfield -d larkfield -c "ALTER TABLE returns ADD COLUMN IF NOT EXISTS qty JSONB;"` (schema.sql only runs on a fresh volume) |
| Answers ignore a new policy | Was ingest rerun? Is `updated` newer than the old article? | Rerun ingest; archive the old article |
| Slow replies (over 30 s) | `ollama ps` shows the model on CPU | Close other GPU apps; keep context at 8k; or switch to `qwen3:14b` |
| Accuracy drops after a change | `evals/report.md` failed-cases list | Fix the article or prompt; rerun the eval |
| A return was wrongly refused | `start_return` error in the request log | Policy lives in `app/tools.py`; change it there and add a test |

## Where things are
- Request log: `logs/requests.jsonl` (PII masked) and the `request_log` table; summary at `/metrics`.
- Tickets and returns created by the agent: `tickets` and `returns` tables.
