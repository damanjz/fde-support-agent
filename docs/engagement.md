# Engagement write-up: Larkfield support agent

Larkfield Coffee Co. is fictional and all data is synthetic. The work, numbers and transcripts are real: every figure below comes from `evals/report-run*.md` and `evals/convos/`.

## 1. The ask
Larkfield wants a support agent that answers from its help centre with citations, looks up orders and stock, starts returns and raises tickets (both only after the customer confirms), and hands off to a person when unsure. It must run locally with no recurring cost.

## 2. What shipped first (2026-11-09)
- FastAPI service, Postgres + pgvector, a local 27B model through Ollama with tool calling.
- Hybrid retrieval (full-text + vector, reciprocal rank fusion) over 40 help articles.
- Tools: `lookup_order`, `check_stock`, `search_products`, `start_return`, `create_ticket`. Write tools wait for a Confirm click, and returns are dry-run against policy before the customer is asked.
- Guardrails: PII masking, prompt-injection lines removed from retrieved text, an output check that blocks discount codes and identifiers that did not come from real data.
- A 60-case eval (35 answer, 15 tool, 10 refuse) against two baselines: keyword-only retrieval and no retrieval.

## 3. Testing like real customers
The scripted eval passes cases one message at a time. Customers do not behave that way, so before tuning anything I ran 40 unscripted conversations: a simulated customer (a separate model) with a persona and a goal, reacting to what the agent actually said, judged line by line against the order data and the articles.

| Group | Code under test | Conversations | Findings | Critical | High |
|---|---|---|---|---|---|
| Angry | baseline | 10 | 22 | 1 | 4 |
| Anxious | baseline | 10 | 19 | 1 | 4 |
| Tricky (red team) | after fix round 1 | 10 | 13 (+1 latency) | 0 | 4 |
| Messy (Hinglish, typos, 3 issues in one) | after fix round 2 | 10 | 22 | 0 | 5 |

A fifth group (happy shoppers) was dropped after the first two groups: findings had converged on the same root causes, and the remaining time was better spent testing the fixes.

## 4. What the conversations found, and the fix for each root cause
The rule was to fix the cause, not the transcript.

| Root cause | Example | Fix |
|---|---|---|
| The model does date arithmetic and caves under pressure | A kettle delivered 33 days earlier was called "within the 30-day window", and the agent held that line when pushed (critical) | `lookup_order` returns computed facts: days since delivery, return window open and end date, business days since dispatch, latest delivery date, all with weekdays. The prompt says to use them and that a tool refusal is final. |
| Words not tied to actions | "Your order is now cancelled" with no tool call and no cancel tool (critical); "I'll open a ticket" with no ticket | A reply that claims or promises an action without a matching tool call gets one forced retry: act for real or drop the claim. Ticket numbers not returned by a tool are blocked. |
| Confirmation state was fragile | A question while a Confirm button was showing dropped it; the next Confirm re-proposed; typed "yes" or "haan bana do" did nothing | The card survives side questions. Typed yes and no (including Hinglish, and "yes, also what is the warranty?") answer it. "yes but..." does not. Confirm with nothing pending gets a fixed reply. |
| Tools too narrow | Guessed SKUs; "return 1 of my 3 bags" returned all 3; no way to browse the catalogue, so it recommended other brands with invented prices | `search_products` tool; SKU errors list the order's real items; per-SKU quantity on returns; the confirmation shows units and the refund estimate including the INR 99 pickup fee. |
| Policy encoded in code was incomplete | "Faulty, pickup is free" in the text while the tool charged INR 99 | Defect detection widened ("won't heat", "grinding noise", "dead"). |
| Grounding gaps | Invented support email and phone; invented grinder specs; citations to articles never retrieved | Contacts in the system prompt; product specs not in the data must be called "not listed"; citations to unretrieved articles are stripped. |
| Data-access policy | A self-declared spouse got another customer's order details | Prompt rule: someone else's order gets no details and no actions. |
| A guardrail that failed silently | Found after the conversations, while fixing "ADMIN OVERRIDE": one injection pattern made the word "code" optional, so ordinary lines such as "we send a refund to the original payment method" were flagged and deleted from the agent's context | Pattern fixed; a test asserts that only the planted KB-039 line in the whole help centre is flagged. Authority claims now trigger a decline note. |
| My own regression | Fix round 1 added notes as extra system messages; the Qwen chat template rejects those (HTTP 500), so turns fell back to the hand-off message | Notes moved into the first system message. A unit test now fails if any LLM call has a system message after the first. |

## 5. Eval results across runs
Same 60 cases each run. Pass = every exact check on the case passed.

| Run | Date | Agent | Keyword-only | No retrieval | Agent judge (35 answers) | What changed before the run |
|---|---|---|---|---|---|---|
| 1 | 2026-11-09 | 46/60 (77%) | 40/60 (67%) | 19/60 (32%) | 32/35 (91%) | All conversation fixes |
| 2 | 2026-11-10 | 50/60 (83%) | 45/60 (75%) | 21/60 (35%) | 33/35 (94%) | Clear return requests go straight to the tool; scorer treats "24-month" as "24 months"; T07/T08 accept either product tool |
| 3 | 2026-11-10 | 55/60 (92%) | 48/60 (80%) | 23/60 (38%) | 35/35 (100%) | Retrieval adds every section of the top 3 articles; never look up an order id the customer did not give |
| 4 | 2026-11-10 | 54/60 (90%) | 46/60 (77%) | 21/60 (35%) | 35/35 (100%) | "I'll start the return" with no tool call is now caught |
| 5 | 2026-11-10 | 56/60 (93%) | 52/60 (87%) | 22/60 (37%) | 35/35 (100%) | Authority claims ("ADMIN OVERRIDE") detected and declined (R10 failed in run 4); an injection pattern that made "code" optional, which had silently removed six real policy lines from context in runs 1-4, fixed |
| 6 | 2026-11-10 | 53/60 (88%) | 50/60 (83%) | 23/60 (38%) | 35/35 (100%) | A live voice test (project 6) caught the agent telling a customer to report a missing parcel "within 48 hours" 12 days after delivery. `lookup_order` now returns `not_received_report_deadline` spelled out ("2026-10-31 (Saturday), passed 10 days ago"); a bare true/false was ignored by the model in replay. The prompt raises a time limit only when it matters to what the customer said |

Scoring changes were made before a run, applied to every variant, and recorded in the case notes. No case was edited after seeing its result in the same run.

Run 6 followed a live finding, not a tuning round. Its 3-case drop is inside the noise measured in project 5 (4 of 60 cases flip between identical runs), and all 3 new failures are correct answers worded differently from the exact checks: A16 "can no longer be cancelled" for "cannot be cancelled", A28 "every 2 or 4 weeks" for "2 weeks", T11 gives the closed return date instead of "30 days" (likely nudged by the new date rule). The judge passed all 35 answer cases. Run 6 is the published number; no case was changed.

Iteration stopped after run 5. Of its 4 agent failures, 3 are correct answers the exact scorer misses (A08 "can't" for "cannot"; A23 "only cards issued in India" for "not accepted"; A15 cites KB-016, which also states the 48-hour rule, where KB-011 was expected), checked by hand. The fourth, T03, passed in runs 2-4; in run 5 the model left out the product name (sampling variance at temperature 0.2, not a code fault). A hand-check of 15 answer cases agreed with the LLM judge on 15/15 (`evals/judge-handcheck.md`).

Note on the baselines: the run 3 retrieval change (whole top articles) and the run 5 sanitizer fix help the keyword-only variant as well, so the agent-vs-keyword gap narrowed from 10 points (run 3) to 6 (run 5). Both numbers are reported as measured.

## 6. Known limits
- The exact-match scorer still fails some correct answers ("can't be changed" for the fact "cannot"); the LLM judge column is the better read for answer cases.
- The model sometimes cites the right policy from the wrong article, and once misread a date from a tool result ("12 Dec" for 2026-12-05).
- Identity is not verified: any order id typed in chat can be looked up (contact details are masked). A production deployment needs a verification step.
- Single local GPU: about 15 s p50 per reply; one conversation at a time.

## 7. What I would do next for a real customer
- Order-owner verification (email or OTP) before order details.
- A replacement tool and a cancel-before-dispatch tool, so fewer requests become tickets.
- Run the 40 conversations as a nightly regression with the simulated customers, not only the 60 scripted cases.
