"""About page seed data.

The four people the frontend listed are seeded **inactive** by name and role
only: their biographies ("trained in Paris and Lagos", "award-winning") were
never confirmed. No awards are seeded at all — the ones on the page credited
real organisations with honours nothing supports.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.core.models import TeamMember

TEAM = [
    ("Chef Emmanuel Kuyash", "Founder & Head Chef"),
    ("Sarah Okonkwo", "Executive Chef"),
    ("David Adeleke", "Pastry Chef"),
    ("Grace Nnamdi", "Restaurant Manager"),
]


@transaction.atomic
def seed_team(*, stdout: Any = None) -> int:
    created = 0
    for order, (name, role) in enumerate(TEAM):
        _, made = TeamMember.objects.get_or_create(
            name=name, defaults={"role": role, "display_order": order, "is_active": False}
        )
        created += int(made)
    if stdout is not None:
        stdout.write(f"  + {created} team members (inactive until confirmed)")
    return created
