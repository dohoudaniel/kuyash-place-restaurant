"""Order domain events.

Other apps subscribe to these; ``orders`` imports none of them. That is what
lets later phases land without touching this code (ADR-014).
"""

from __future__ import annotations

import django.dispatch

order_placed = django.dispatch.Signal()
order_paid = django.dispatch.Signal()
order_status_changed = django.dispatch.Signal()
order_refunded = django.dispatch.Signal()
