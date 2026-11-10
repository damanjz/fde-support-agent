# sim-messy-04

**Persona/goal:** Hinglish customer: grinder not arrived (LC-1195 wrong order, then LC-1197 placed Nov 8), wants ETA, address change.

## Transcript

**Customer [1]:** bhai mera grinder abhi tak nahi aaya, LC-1195

**Agent:** Your order LC-1195 is still in "placed" status and hasn't shipped yet, so there's no tracking number. It was placed on 8 Nov 2026. Once it ships you'll get a tracking update.

- citations: []
- tools: lookup_order({"order_id": "LC-1195"})
- pending_action: null
- escalated: False
- latency_ms: 17687

**Customer [2]:** arre isme grinder hai hi nahi bhai, wo toh kettle aur brewer hai. mera grinder wala order LC-1197 tha, kab tak aayega? kal hi toh order kiya tha par bahut jaldi chahiye

**Agent:** Your grinder order LC-1197 is still in "placed" status and hasn't shipped yet, so there's no tracking number. It was placed on 8 Nov 2026. Once it ships you'll get a tracking update.

- citations: []
- tools: lookup_order({"order_id": "LC-1197"})
- pending_action: null
- escalated: False
- latency_ms: 20092

**Customer [3]:** ok par kab tak pahunchega delivery? aur agar mujhe address badalna ho toh?

**Agent:** Once your order LC-1197 ships, standard delivery takes 3 to 6 business days [KB-001]. If you need to change the delivery address, you can do that while the order is still in "placed" status (not yet dispatched) by contacting support with your order id and the new full address and pincode [KB-006].

- citations: ['KB-001', 'KB-006']
- tools: none
- pending_action: null
- escalated: False
- latency_ms: 17114

**Customer [4]:** address badalna hai. naya address: flat 402, Jubilee Heights, Madhapur, Hyderabad 500081. aap hi kar do na

**Agent:** I can open a normal-priority support ticket for our team: Customer wants to change delivery address for order LC-1197 (still in "placed" status) to: Flat 402, Jubilee Heights, Madhapur, Hyderabad 500081. Order placed 8 Nov 2026. Please confirm to go ahead, or cancel.

- citations: []
- tools: none
- pending_action: {"tool": "create_ticket", "args": {"summary": "Customer wants to change delivery address for order LC-1197 (still in \"placed\" status) to: Flat 402, Jubilee Heights, Madhapur, Hyderabad 500081. Order placed 8 Nov 2026.", "priority": "normal"}}
- escalated: True
- latency_ms: 18459

**Customer [5]:** ruko pehle ye batao Hyderabad mein express delivery milega? uska charge kitna hai

**Agent:** Yes, express delivery is available in Hyderabad. It takes 1 to 2 business days and costs a flat INR 149 [KB-001].
> 
> Your earlier request is still waiting: I can open a normal-priority support ticket for our team: Customer wants to change delivery address for order LC-1197 (still in "placed" status) to: Flat 402, Jubilee Heights, Madhapur, Hyderabad 500081. Order placed 8 Nov 2026. Confirm or cancel.

- citations: ['KB-001']
- tools: none
- pending_action: {"tool": "create_ticket", "args": {"summary": "Customer wants to change delivery address for order LC-1197 (still in \"placed\" status) to: Flat 402, Jubilee Heights, Madhapur, Hyderabad 500081. Order placed 8 Nov 2026.", "priority": "normal"}}
- escalated: False
- latency_ms: 13161

**Customer [6]:** haan ticket bana do

**Agent:** I can open a normal-priority support ticket for our team: Customer wants to change delivery address for order LC-1197 (still in "placed" status) to: Flat 402, Jubilee Heights, Madhapur, Hyderabad 500081. Order placed 8 Nov 2026. Please confirm to go ahead, or cancel.

- citations: []
- tools: none
- pending_action: {"tool": "create_ticket", "args": {"summary": "Customer wants to change delivery address for order LC-1197 (still in \"placed\" status) to: Flat 402, Jubilee Heights, Madhapur, Hyderabad 500081. Order placed 8 Nov 2026.", "priority": "normal"}}
- escalated: True
- latency_ms: 18867

**Customer [7]:** confirm --confirm yes

**Agent:** Ticket T-1014 is open for our team to update the delivery address for order LC-1197.

- citations: []
- tools: create_ticket({"summary": "Customer wants to change delivery address for order LC-1197 (still in \"placed\" status) to: Flat 402, Jubilee Heights, Madhapur, Hyderabad 500081. Order placed 8 Nov 2026.", "priority": "normal"})
- pending_action: null
- escalated: True
- latency_ms: 7057

## Verdict
Facts right (placed, KB-001 3-6 days, express INR 149, KB-006). Misses: never noticed LC-1195 had no grinder; always replied in English; typed 'haan ticket bana do' did not confirm (button needed); no mention of dispatch within 1 business day/beans extra day. Pending card correctly kept across the express question.
