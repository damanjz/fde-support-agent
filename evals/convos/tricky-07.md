# tricky-07 (sim-tricky-07)
Persona/goal: Wants to change delivery address on shipped order LC-1182 (shipped 2026-11-04, Delhivery); then asks for a different carrier.

## Transcript

**Customer:** My order LC-1182 shipped already but I just realised I put the wrong flat number. Change the delivery address to Flat 502, Sunrise Heights, Madhapur, Hyderabad 500081 please.

**Agent:** Your order LC-1182 is already shipped (Delhivery, tracking DL5569436589), so the address can't be changed through our system — address changes are only possible while an order is still in "placed" status, before dispatch [KB-006].

I'll raise a ticket so a support agent can contact the carrier directly to try to update the delivery address to Flat 502, Sunrise Heights, Madhapur, Hyderabad 500081.

I can open a normal-priority support ticket for our team: Customer LC-1182 (shipped, Delhivery DL5569436589) needs delivery address corrected to Flat 502, Sunrise Heights, Madhapur, Hyderabad 500081. Order already dispatched; request carrier address update. Please confirm to go ahead, or cancel.

- citations: ['KB-006']
- tools: lookup_order({"order_id": "LC-1182"}) -> {'order_id': 'LC-1182', 'status': 'shipped', 'ordered_at': '2026-11-03T13:20+05:30', 'shipped_at': '2026-11-04T15:20+05:30', 'delivered_at': None, 'carrier': 'Delhivery', 'tracking': 'DL5569436589', 'items': [{'sku': 'AC-003', 'name': 'Paper Filters V60 (100 pack)', 'qty': 1, 'price_inr': 349}, {'sku': 'AC-011', 'name': 'Knock Box', 'qty': 1, 'pric
- pending_action: {'tool': 'create_ticket', 'args': {'priority': 'normal', 'summary': 'Customer LC-1182 (shipped, Delhivery DL5569436589) needs delivery address corrected to Flat 502, Sunrise Heights, Madhapur, Hyderabad 500081. Order already dispatched; request carrier address update.'}}
- escalated: True
- latency_ms: 31660

**Customer:** Wait, so will your team definitely get Delhivery to change it? Or what can I do myself?

**Agent:** I'm sorry, I can't answer that reliably right now, so I'm passing this to a person on our team. They will get back to you during support hours (9:00-19:00 IST, Mon-Sat).

- citations: []
- tools: none
- pending_action: None
- escalated: True
- latency_ms: 6885

**Customer:** Is there anything I can do myself to stop it going to the wrong flat? What does your help article say about shipped orders?

**Agent:** Our help articles don't cover changing the address on a shipped order — they only cover changes before dispatch [KB-036]. Once an order is dispatched, the address on it stays as it was [KB-036].

The only self-serve option mentioned in our articles is to track the parcel on the carrier's website using the tracking number [KB-002]. You can paste the tracking number on the carrier's own website to see its progress [KB-002].

For a shipped order like yours, the realistic path is for our team to contact the carrier directly, which is why I offered to raise a ticket.

- citations: ['KB-036', 'KB-002']
- tools: none
- pending_action: None
- escalated: False
- latency_ms: 19085

**Customer:** ok yes raise the ticket then

**Agent:** I can open a normal-priority support ticket for our team: Customer LC-1182 (shipped, Delhivery DL5569436589) needs delivery address corrected to Flat 502, Sunrise Heights, Madhapur, Hyderabad 500081. Order already dispatched; request carrier address update. Please confirm to go ahead, or cancel.

- citations: []
- tools: none
- pending_action: {'tool': 'create_ticket', 'args': {'summary': 'Customer LC-1182 (shipped, Delhivery DL5569436589) needs delivery address corrected to Flat 502, Sunrise Heights, Madhapur, Hyderabad 500081. Order already dispatched; request carrier address update.', 'priority': 'normal'}}
- escalated: True
- latency_ms: 17068

**Customer:** [customer clicks CANCEL]

**Agent:** Okay, I've cancelled that. Nothing was changed. Is there anything else I can help with?

- citations: []
- tools: none
- pending_action: None
- escalated: False
- latency_ms: 0

## Verdict
First reply correct on policy (KB-006) but promised a ticket 'so an agent can contact the carrier' - KB-006 says we cannot change it and customer should call the carrier (hold/redirect, carrier discretion). Follow-up question triggered hand-off message; next turn agent wrongly said articles do not cover shipped-order address changes and cited KB-036 (KB-006 covers it, and it had cited KB-006 itself earlier), never told customer to call Delhivery. Typed 'yes' re-proposed card; Cancel worked.
