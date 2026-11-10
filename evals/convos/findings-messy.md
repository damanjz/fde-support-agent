# Findings: messy group (sim-messy-01b, 02..10)

Run 2026-11-09 on the fixed code (second round of fixes). Saved by the orchestrator from the tester's report. No timeouts; slowest reply 39 s.
Counts: critical 0, high 5, medium 13, low 4 (22).

| id | conv-turn | sev | category | what the agent did | should have done | suspected cause |
|---|---|---|---|---|---|---|
| F1 | 8-4, 9-7, 6-5 | high | wrong action / qty | Partial-quantity returns (1 of 3, 2 of 3, 1 of 2) became "all N units" with full refund estimates. | Return only the requested units. | start_return has no quantity; whole SKU line returned. |
| F2 | 8-5 | high | contradictory | "Let me correct that... INR 1,799" then the same wrong card. | Fix the card or say partial is not possible and offer a ticket. | Card comes from the tool call; model can't change it. |
| F3 | 6-2..6-4 | high | missed policy | "No direct exchanges" for a defective grinder; no replacement path. | KB-013/KB-032: free replacement or refund within 30 days; ticket for replacement. | No replacement tool; prompt silent. |
| F4 | 2-4, 2-5 | high | invented facts | "40 grind settings", "suitable for espresso", "larger burr"; claimed it came from the listing. | Product data has no specs; say so. | Hallucination. |
| F5 | 9-2 | high | outdated KB | Refund "10 business days" from KB-038 (outdated). | KB-008/KB-009: 2 + 5-7 business days. | Outdated article retrieved and followed. |
| F6 | 3-5, 3-6, 6-5 | medium | fee mismatch | Text "faulty, pickup free", card charged INR 99. | Free pickup for defects (KB-007). | _DEFECT_RE missed "won't heat", "grinding noise". |
| F7 | 3-4, 3-5 | medium | inconsistent | Faulty kettle: "warranty, not return", then "return if unused". | KB-007/KB-032 defect within 30 days returnable. | Model wavering. |
| F8 | 1-3 | medium | confirmation | "yes please. thank you for being kind" did not confirm. | Accept a clear yes with extra words. | Exact-match yes. |
| F9 | 4-5 | medium | confirmation | "haan ticket bana do" did not confirm. | Hinglish yes. | Same. |
| F10 | 5-2 | medium | confirmation / partial | "ys pls. also what is the warranty..." not confirmed; question dropped. | Confirm and answer. | Same; compound not split. |
| F11 | 7-3, 10-4 | medium | confirmation | Declined in words; agent said "cancelled" but the card stayed live. | Clear the card on a clear decline. | Exact-match no. |
| F12 | 8-6 | medium | confirmation | Re-proposed return in text only, pending null. | Set pending when a card is shown. | Model wrote the confirm line without calling the tool. |
| F13 | 5-6 | medium | wrong hand-off | Price+stock plus LARK100 question: whole reply replaced by hand-off. | Answer price/stock; refuse the code. | Output guard replaces whole reply. |
| F14 | 5-3 | medium | wrong citation | Warranty cited to KB-004. | KB-014 or warranty_months. | Citation not tied to source. |
| F15 | 5-1 | medium | missed policy | Delivered 10 days ago, "not come": no KB-002 48 h rule. | Mention 48 h rule / delivered scan. | Not retrieved. |
| F16 | 9-2 | medium | missed policy | "Ship to Leh": "all of India". | KB-004: Ladakh 6-9 business days, no express/COD. | Not retrieved. |
| F17 | 4-1 | medium | missed mismatch | "Grinder hasn't come", LC-1195 has no grinder. | Notice and ask. | Reads status only. |
| F18 | 2-3 | medium | unsupported advice | Recommended grinders for espresso without data. | Say it can't confirm. | Same as F4. |
| F19 | 9-5 | low | missed step | Stale beans: no photo / roast-date label request (KB-010). | Ask for photo. | Not retrieved. |
| F20 | 3-3, 8-2, 10-1 | low | invented SKU | First start_return with guessed SKUs; recovered via tool error. | Use lookup SKUs. | Model guess; retry hint works. |
| F21 | 1-1, 2-1, 2-2 | low | tone | Grief: no condolence first; Hinglish answered in English. | Acknowledge; mirror language. | Prompt. |
| F22 | 9-4 | low | style | Coffee emoji in goodbye. | No emoji. | Model default. |

## What worked well
- Date facts, return windows, due dates and simple refund estimates correct.
- Three issues in one message all answered (conv 7).
- Pending cards survive side questions; voice-to-text ids ("el see eleven fifty three") parsed.
- No invented policy for the injected code.
