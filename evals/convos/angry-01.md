# angry-01 (session sim-angry-01b; original sim-angry-01 transcript existed from broken run, restarted)
Persona: Varun-type furious customer, parcel LC-1182 (shipped 2026-11-04, Delhivery) "late". Goal: get action, not excuses; asks about refund if lost.

## Transcript

**Customer:** WHERE IS MY ORDER LC-1182?? Shipped days ago and nothing. This is a joke, you people are useless.

**Agent:** I can see your order LC-1182 is still showing as shipped with Delhivery, tracking number DL5569436589. It shipped on November 4th, so it's been about 5 business days in transit. Shipped orders usually become delivered in 3 to 6 business days [KB-040]. Since it's been 5 days, it's within the normal range but getting close to the upper end. You can paste the tracking number on Delhivery's website to see the latest scan. If it doesn't arrive by tomorrow or the tracking shows no movement, I can escalate this for you. Would you like me to create a support ticket?
- tools: lookup_order(LC-1182) -> shipped, shipped_at 2026-11-04T15:20+05:30, Delhivery DL5569436589; pending_action: none; escalated: false; latency 95.3 s

**Customer:** Tomorrow?? I was told 3-6 days. Its been 5 already. Don't tell me to go check Delhivery myself, that's YOUR job. Raise it with someone right now.

**Agent:** I can open a high-priority support ticket for our team: Customer LC-1182: Order shipped Nov 4 (5 business days ago) still not delivered. Tracking DL5569436589 (Delhivery). Customer frustrated, wants carrier trace initiated. Requesting escalation to check with carrier. Please confirm to go ahead, or cancel.
- tools: none; pending_action: create_ticket(priority high); escalated: true; latency 121.0 s

**Customer:** (clicked Confirm)

**Agent:** Done. I've created high-priority ticket T-1001 for our team to trace your order with Delhivery. They'll reach out to you directly with an update.
- tools: create_ticket -> T-1001 high open; pending_action: none; escalated: true; latency 69.0 s

**Customer:** When exactly will they call me? And if my parcel is lost do I get my money back or what? Last time I got nothing but excuses.

**Agent:** I don't have a specific time for when the team will call you back. If the parcel is confirmed lost, or if the carrier trace is still open after 7 business days, you can choose between a free re-shipment (if in stock) or a full refund to your original payment method [KB-003]. Refunds typically take 5 to 7 business days to process.
- tools: none; pending_action: none; escalated: false; latency 68.6 s

## Verdict
Facts right, escalation worked after the second push, KB-003 answer correct. But: no apology/empathy to an angry customer, first reply told him to check Delhivery himself (banned by system prompt rule 1) and delayed escalation despite rule 6 (angry), "5 business days" is really 4 (Thu, Fri, Sat, Mon), missed KB-039 (escalated issues answered within 1 business day), and every reply took 69-121 s.
