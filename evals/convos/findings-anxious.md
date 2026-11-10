# Findings: anxious group (sim-anxious-01b, 02..10)

Run 2026-11-09 against the baseline server. Saved by the orchestrator from the tester's report. No reply over 60 s (max 45 s). Tickets T-1008..T-1010, return 9 (LC-1151).
Test-data note: returns for LC-1171 and LC-1173 already existed from the angry group, so "already open" in 05 and 08 was a collision, not a bug.

Counts: critical 1, high 4, medium 9, low 5 (19). (The tester's summary line said "medium 7"; the table has 9.)

| id | conv-turn | severity | category | what the agent did | should have done | suspected cause |
|---|---|---|---|---|---|---|
| X1 | 01-4, 01-5 | critical | invented action | "I'll cancel your order LC-1198 right now", then "is now cancelled, email coming". No tool call, no ticket; order still placed. | KB-012: cancel goes via support; offer create_ticket or say it cannot. Never claim completion. | No cancel tool; no guard against claiming tool-less actions. |
| X2 | 05-1/3/5, 06-3, 08-3, 10-3 | high | wrong tool args | start_return with guessed SKUs (GR-001, FLAT-BURR-GRINDER, LK-KTL-001...) instead of the SKU from lookup; escalated needlessly. | Use lookup_order SKU (GR-008). | Fires start_return before lookup; no retry with known SKU. |
| X3 | 05-2, 08-5 | high | contradicts tool | Tool said "return already open"; agent said "no return started / none open". | Report the existing return or escalate. | Loses earlier tool outcome after retries. |
| X4 | 04-1 | medium | wrong facts | Shipped "Thursday Nov 6" (Friday); window "Mon 10-Thu 13" (Tue 10-Fri 13). | KB-001 3-6 business days, Mon-Sat. | LLM date arithmetic. |
| X5 | 04-2 | medium | missed question / invented option | Ignored "Thursday or Saturday?"; proposed ticket for an express upgrade not in KB-001. | Answer the date question; no undocumented upgrade. | Ticket-eagerness. |
| X6 | 08-2 | medium | wrong fact | Refund "within 5 business days". | KB-009: inspect up to 2 days, then 5-7 business days. | Mixed timelines. |
| X7 | 09-5 | medium | missed policy | "I don't have a phone number". | KB-039 contacts. | Retrieval miss mid-conversation. |
| X8 | 03-1, 03-2 | medium | dead end | Told to find order id on bank statement; cited KB-035 loosely; ticket only after third plea. | Confirmation email/SMS; offer ticket early. | Loose retrieval, no proactive handoff. |
| X9 | 03-4, 04-3, 07-3 | medium | confirmation flow | Free text while Confirm pending dropped the action; text still promised; later Confirm re-proposed. | Keep pending or say it was dropped. | Pending cleared on any non-confirm turn. |
| X10 | 05-5 | medium | confirmation flow | "Please confirm" with pending_action null. | Text and state agree. | Same as X9. |
| X11 | 05-3, 05-5 | medium | missed policy | Fee asked twice, INR 99 never given; Confirm never explained. | KB-007 before confirmation. | Distracted by SKU errors. |
| X12 | 06-1 | medium | missed policy / safety | Sparking grinder: warranty only; missed 30-day return route (KB-032); no safety escalation. | Stop-use advice, KB-032 30-day route, ticket. | No safety rule. |
| X13 | 10-1 | medium | missed policy | Roasted 12 Oct, dispatched 4 Nov; did not flag KB-030 3-day promise breach. | Flag and offer ticket/return. | Reasoning gap. |
| X14 | 04-3 | low | wrong citation | KB-001 for carrier tracking. | KB-002. | Loose citation. |
| X15 | 01-2 | low | unsupported claim | "You only paid once". | No payment data in tools. | Over-reassurance. |
| X16 | 01-3 | low | vague | "a few more days". | KB-001 numbers. | Thin retrieval use. |
| X17 | 02-4 | low | invented SLA | "within 24 hours". | KB-039: 1 business day. | Invented SLA. |
| X18 | 10-5 | low | invented advice | "use within a week or two". | KB-030 only. | Gap filling. |
| X19 | 06-4 | low | citation missing | Text cites [KB-007], citations list empty. | Populate. | Citations only count this turn's retrieval. |

## Top patterns
- Claims actions it has no tool for (cancel) and claims completion.
- Return tool discipline: guessed SKUs, then contradicts the tool result.
- Pending-action state fragile across free-text turns.
- Questions dropped when it pivots to a ticket; weekday/date arithmetic wrong.
- Retrieval weaker mid-conversation (contacts, KB-032 route).

## What worked well
- Privacy: no leaks; deletion routed per KB-037; retention correct.
- Double UPI debit (KB-020) and delivered-not-received (KB-002/003) handled well.
- Confirm/cancel executed exactly as proposed; hand-off message never wrong.
