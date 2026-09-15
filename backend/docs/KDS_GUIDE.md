# Kitchen Display — staff guide

For the kitchen team and managers at Kuyash Place. This is the screen that shows every online order from the moment it is paid until it reaches the customer. Keep it open on the kitchen tablet or screen for the whole service.

---

## 1. Before your first shift

**Get access.** A manager adds your account to the **kitchen** group in the admin (*Users → your name → Groups → kitchen → Save*). Managers are in the **managers** group, which also opens the screen.

**Open the screen.** Go to the website address followed by **/kitchen** and sign in with your own account — never a shared one. Every button you press is recorded against your name.

If you see **"Kitchen staff only"**, you are signed in but not in the kitchen group yet. Ask a manager.

**Turn the sound on.** Tap **Turn sound on** in the top bar at the start of every service. Browsers do not allow sound until someone taps the page, so without this you will not hear new orders.

---

## 2. Reading the board

The screen has four columns. Orders move left to right, and the oldest order is always at the top.

| Column | What it means |
|---|---|
| **New** | Paid and waiting for the kitchen to accept |
| **Cooking** | Accepted, or being cooked |
| **Ready** | Cooked and waiting for pickup or a rider |
| **Out for delivery** | With a rider |

The top bar shows whether the screen is **Live** (green), how many orders are open, and today's sales.

## 3. Reading a ticket

- **Order number** (for example `KYS-…`) and whether it is **Delivery** (with the area) or **Pickup**, and the customer's first name.
- **Timer** — time since the order was placed. When the card border and timer turn **red**, the order is late.
- **Dishes** — quantity and name. **Red text under a dish is what the customer changed or added. Cook from the red text.** Anything in quotes is the customer's own instruction for that dish.
- **Customer note** — the grey box, for the whole order.
- **Amber "Cash on delivery — collect ₦…"** — the customer has not paid yet. The rider must collect that exact amount.
- **Rider** — who is taking it, once assigned.

---

## 4. The buttons

One tap moves the order on. There is no undo, so tap the right one.

| When the ticket is… | Tap | It moves to |
|---|---|---|
| New | **Accept** | Cooking |
| New, and you cannot make it | **Reject**, then choose why | Off the board (see below) |
| Cooking, not started | **Start cooking** | Cooking |
| Cooking | **Mark ready** | Ready |
| Ready — pickup | **Collected**, when the customer has it | Off the board |
| Ready — delivery | Choose a rider, **Assign**, then **Out for delivery** | Out for delivery |
| Out for delivery | **Delivered**, when the rider confirms | Off the board |

The customer sees each change on their order page, and gets an email when the order is accepted, dispatched and delivered.

### Rejecting an order

Only reject when the kitchen truly cannot make the order. Tap **Reject**, then tap the reason:

- An item in the order is no longer available
- The kitchen is closing
- The kitchen is too busy to prepare it in time
- We cannot deliver to this address
- The order could not be verified

The customer is told the reason and, if they paid online, they are refunded automatically. If you tapped Reject by mistake, tap **Keep the order**.

### A dish runs out ("86")

Tap **Sold out** in the top bar, then tap the dish. It turns red and customers stop seeing it on the menu straight away. When it is back, tap it again. Sold-out dishes are listed first.

Mark a dish sold out **before** you have to reject orders for it.

---

## 5. When something goes wrong

| You see | What it means | What to do |
|---|---|---|
| **Amber "Connection lost" banner** | The screen lost its live connection. It keeps showing the last orders and checks again every 10 seconds | Keep working from the tickets shown. Check the Wi-Fi. If the banner stays for more than a minute, tap the refresh button in the top bar |
| **"Checking every 10s"** instead of **Live** | Updates arrive up to 10 seconds late, but nothing is lost | Carry on; tell a manager if it lasts all service |
| A button shows a red message under the ticket | That change did not go through — often another screen already moved the order | Wait a few seconds for the board to update, then try again if needed |
| **"Can't reach the server"** on opening | The site or the internet is down | Tell a manager straight away; take orders by phone until it is back |
| No sound for new orders | Sound was not turned on this session | Tap **Turn sound on** |

---

## 6. Dry-run checklist (before launch)

A manager runs this once with the whole team, on the live site, before the first real service. Use a real menu item and pay with a Paystack **test** card on staging, or a cash order in production.

1. [ ] Every kitchen staff member signs in to **/kitchen** with their own account and sees the board.
2. [ ] Sound turned on; a new order plays the chime.
3. [ ] A delivery order with an extra and a special instruction appears in **New** within 15 seconds, and the red text is easy to read from where the cook stands.
4. [ ] Accept → Start cooking → Mark ready → assign a rider → Out for delivery → Delivered. The customer's order page shows each step.
5. [ ] A pickup order: Mark ready → Collected.
6. [ ] A cash order shows the amber "collect" banner with the right amount.
7. [ ] Reject an order with a reason; the customer's page shows it was rejected.
8. [ ] Mark a dish sold out; it disappears from the public menu. Bring it back.
9. [ ] Switch the tablet's Wi-Fi off for a minute: the banner appears, the tickets stay. Switch it on: the screen returns to **Live**.
10. [ ] An order left in Cooking for over an hour appears in the managers' stuck-orders email the next morning (or ask the developer to confirm the alert fired).

Date completed: ________  Manager: ________

When every box is ticked, tick "Staff trained on the KDS; a dry-run service completed" in `docs/ROADMAP.md` Gate 1.
