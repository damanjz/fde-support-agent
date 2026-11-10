# LLM judge hand-check

2026-11-10. Asked for by the spec audit: is the judge column trustworthy?

## Method
- Run 5 (`evals/results/20261110-023435-agent.jsonl`), fixed sample: every second answer case (A01, A03, ... A29), 15 cases.
- For each reply I checked every claim against the source articles in `data/articles/`, not only the expected facts, and gave my own pass/fail before comparing with the judge.

## Result
| | Count |
|---|---|
| Cases checked | 15 |
| Human pass | 15 |
| Judge pass | 15 |
| Agreement | 15/15 |
| Exact scorer pass on the same cases | 13/15 |

- The two exact-scorer failures are wording and citation strictness, not wrong answers:
  - A15 cites KB-016 for the 48-hour damage rule. KB-016 does state it ("Report arrival damage within 48 hours"); the case expects KB-011, which states it too.
  - A23 says "we only accept credit and debit cards issued in India"; the expected phrase is "not accepted".
- Extra claims checked against the articles and found supported: A07 (INR 40 COD fee, KB-005/KB-019), A13 (stale, foreign matter, KB-010), A19 (8-year invoice retention, KB-037), A25 (standard EMI 3/6/9 months, KB-021), A29 (changes after the cut-off apply to the following delivery, KB-025).

## Limits
- This sample has no failures, so it shows the judge does not reject correct answers; it does not show the judge catches wrong ones. Evidence for that comes from earlier runs, where the judge failed real errors: run 1 A03 (said the express fee is not listed; KB-001 has INR 149) and A24 (missed the 5-7 day timeline).
- One checker (me) and 15 cases. Read the judge column as a strong signal, not ground truth.
