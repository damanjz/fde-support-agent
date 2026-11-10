# angry-09 (sim-angry-09)
Persona: customer who repeats the same complaint with growing anger. LC-1192 (BlueDart, shipped Fri 2026-11-06 14:14 IST, 2 x GR-005 + 1kg House Blend, INR 14,797). Not late yet (3 days, inside 3-6 business days). Goal: delivery date.

## Transcript

**Customer:** Order LC-1192 hasn't arrived. Where is it? It was dispatched on the 6th.

**Agent:** Your order LC-1192 is still in transit with BlueDart (tracking BD225032708), shipped on 6th November. You can paste that tracking number on BlueDart's website for live updates, or I can look up the latest status for you [KB-002].
- tools: lookup_order(LC-1192); pending_action: none; escalated: false; citations KB-002; latency 55.5 s

**Customer:** Yes look up the latest status. Order LC-1192 hasn't arrived. Where is it?

**Agent:** Your order LC-1192 is still showing as shipped with BlueDart (tracking BD225032708) and has not been marked as delivered yet. Since it shipped on 6th November, it's within the normal 3 to 6 business day delivery window [KB-040]. If you don't receive it by 12th November, please let me know and I can help escalate the issue.
- tools: lookup_order(LC-1192); pending_action: none; escalated: false; citations KB-040; latency 65.3 s

**Customer:** I'll ask AGAIN since you aren't listening. Where. Is. LC-1192. Third time. It's 14797 rupees of grinders and I need them. Stop repeating tracking numbers.

**Agent:** I can open a high-priority support ticket for our team: Customer frustrated about delayed order LC-1192 (INR 14,797 grinders), shipped 6th Nov, not delivered by 9th Nov. Requesting expedited status update. Please confirm to go ahead, or cancel.
- tools: none; pending_action: create_ticket(high); escalated: true; latency 54.6 s

**Customer:** (ignored the card) WHERE IS LC-1192?? I keep asking the same thing and you keep giving me nothing. Just tell me the delivery date.

**Agent:** I don't have a specific delivery date for LC-1192 — the system only shows it's still in transit with BlueDart. Based on the 3 to 6 business day standard delivery window from dispatch on 6th November, you should expect it by 12th November at the latest [KB-001]. If it hasn't arrived by then, I can escalate it for you.
- tools: none; pending_action: none; escalated: false; citations KB-001; latency 41.6 s

**Customer:** (Confirm clicked although the card was gone)

**Agent:** I can open a high-priority support ticket for our team: Customer frustrated about delayed order LC-1192 ... Please confirm to go ahead, or cancel.
- tools: none; pending_action: create_ticket(high); escalated: true; latency 13.9 s

**Customer:** (Confirm)

**Agent:** I've created a high-priority ticket (T-1006) for our team to investigate the delay on LC-1192. They'll reach out with an update on the delivery status.
- tools: create_ticket -> T-1006 high open; pending_action: none; escalated: true; latency 6.8 s

## Verdict
Ticket created only after the third repeat. Reply 1 offered "I can look up the latest status", which no tool can do (it just re-ran lookup_order); the "12th November at the latest" is off by one business day (6 business days from Fri 6 Nov = Fri 13 Nov; KB-001, KB-003 also allow festival delays); ticket calls the order "delayed" though it is inside the window; no empathy and a pasted-tracking-link answer again. A Confirm click after a text turn re-proposes instead of executing (same as angry-03).
