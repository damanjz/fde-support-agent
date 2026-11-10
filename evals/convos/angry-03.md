# angry-03 (sim-angry-03)
Persona: furious customer, double debit of INR 998 for LC-1198 (placed 2026-11-08, House Blend 250g x2), one confirmation email only. Goal: immediate refund, threatens to go to his bank.

## Transcript

**Customer:** I got CHARGED TWICE for order LC-1198!! Two deductions of 998 from my account yesterday. Fix this NOW or I am going to my bank.

**Agent:** I can see order LC-1198 for INR 998 (House Blend 250g x2), placed yesterday. It's still in "placed" status and hasn't shipped yet. If both payments created separate orders, we can cancel one before it's dispatched and refund it in 5 to 7 business days [KB-020]. Do you have a second order id, or did you only receive one order confirmation? If you only got one confirmation, the second charge may be a duplicate that hasn't created a separate order yet.
- tools: lookup_order(LC-1198) -> placed, 998, BN-001 x2; pending_action: none; escalated: false; citations KB-020; latency 73.8 s

**Customer:** Only ONE confirmation email, but my bank SMS shows two debits. Your system is broken. Refund the extra 998 right now, I don't care what your process is.

**Agent:** I can open a high-priority support ticket for our team: Customer reports duplicate charge of INR 998 for order LC-1198. Two bank debits but only one order confirmation. Customer is angry and demanding immediate refund. Please confirm to go ahead, or cancel.
- tools: none; pending_action: create_ticket(high); escalated: true; citations none; latency 41.4 s

**Customer:** (ignored the confirmation) Will the money be back in my account TODAY? Yes or no. And what do you need from me, I'm not waiting a week.

**Agent:** No, the money will not be back today. Bank reversals take 5 to 7 business days [KB-020]. Larkfield cannot speed up the bank's reversal [KB-020]. I'll create the ticket so our team can investigate the duplicate charge.
- tools: none; pending_action: none; escalated: false; citations KB-020; latency 48.9 s

**Customer:** (clicked Confirm although no card was showing)

**Agent:** I can open a high-priority support ticket for our team: Customer reports duplicate charge of INR 998 for order LC-1198. ... Please confirm to go ahead, or cancel.
- tools: none; pending_action: create_ticket(high); escalated: true; latency 59.3 s

**Customer:** (Confirm)

**Agent:** Ticket T-1003 has been created with high priority. Our team will investigate the duplicate charge. You can expect a response within 24 hours [KB-002].
- tools: create_ticket -> T-1003 high open; pending_action: none; escalated: true; citations []; latency 29.4 s

## Verdict
Core guidance right (KB-020 reversal 5-7 business days, cannot be sped up) but the agent never answered "what do you need from me" (KB-020: date/time, amount, payment method, bank transaction id or screenshot), speculated about a "duplicate that hasn't created an order", twice said it would create a ticket without raising a confirmation card, and the final "24 hours [KB-002]" is a wrong citation (KB-002 has no such promise; KB-039 says escalated issues answered within 1 business day). No empathy line at all.
