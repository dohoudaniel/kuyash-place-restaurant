"""Academy seed data, carried over from ``app/academy/page.tsx``.

Seeded **inactive**. The instructor names, course fees and descriptions were
hardcoded in the frontend beside invented ratings and student counts, and no
class dates existed at all. Staff review each course, confirm the instructor
and fee, schedule a cohort and only then publish it.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from apps.academy.models import Course, Instructor

INSTRUCTORS = [
    "Chef Emmanuel Kuyash",
    "Chef David Adeleke",
    "Chef Sarah Okonkwo",
    "Grace Nnamdi",
    "Dr. Amina Ibrahim",
]

COURSES: list[dict[str, Any]] = [
    {
        "slug": "nigerian-cuisine-fundamentals",
        "title": "Nigerian Cuisine Fundamentals",
        "description": "Master the basics of traditional Nigerian cooking",
        "instructor": "Chef Emmanuel Kuyash",
        "level": "beginner",
        "course_type": "cooking",
        "duration_label": "4 weeks",
        "session_count": 8,
        "price": 5_000_000,
        "features": ["Hands-on Practice", "Recipe Book", "Certificate"],
    },
    {
        "slug": "advanced-pastry-and-baking",
        "title": "Advanced Pastry & Baking",
        "description": "Professional techniques for breads, cakes, and pastries",
        "instructor": "Chef David Adeleke",
        "level": "advanced",
        "course_type": "baking",
        "duration_label": "6 weeks",
        "session_count": 12,
        "price": 7_500_000,
        "features": ["Small Class", "Equipment Included", "Certificate"],
    },
    {
        "slug": "restaurant-plating-and-presentation",
        "title": "Restaurant Plating & Presentation",
        "description": "Learn the art of beautiful food presentation",
        "instructor": "Chef Sarah Okonkwo",
        "level": "intermediate",
        "course_type": "plating",
        "duration_label": "3 weeks",
        "session_count": 6,
        "price": 4_000_000,
        "features": ["Photography Tips", "Portfolio Building", "Certificate"],
    },
    {
        "slug": "restaurant-business-management",
        "title": "Restaurant Business Management",
        "description": "Everything you need to start and run a restaurant",
        "instructor": "Grace Nnamdi",
        "level": "intermediate",
        "course_type": "business",
        "duration_label": "5 weeks",
        "session_count": 10,
        "price": 6_000_000,
        "features": ["Business Plan Template", "Mentorship", "Certificate"],
    },
    {
        "slug": "nutrition-and-menu-planning",
        "title": "Nutrition & Menu Planning",
        "description": "Create balanced, healthy menus that taste great",
        "instructor": "Dr. Amina Ibrahim",
        "level": "intermediate",
        "course_type": "nutrition",
        "duration_label": "4 weeks",
        "session_count": 8,
        "price": 4_500_000,
        "features": ["Meal Plans", "Nutrition Charts", "Certificate"],
    },
    {
        "slug": "culinary-masterclass",
        "title": "Culinary Masterclass",
        "description": "Exclusive intensive with Chef Emmanuel",
        "instructor": "Chef Emmanuel Kuyash",
        "level": "masterclass",
        "course_type": "cooking",
        "duration_label": "2 weeks",
        "session_count": 10,
        "price": 15_000_000,
        "features": ["1-on-1 Sessions", "Premium Ingredients", "Master Certificate"],
    },
]


@transaction.atomic
def seed_academy(branch: Any, *, stdout: Any = None) -> int:
    instructors = {}
    for name in INSTRUCTORS:
        instructors[name], _ = Instructor.objects.get_or_create(
            name=name, defaults={"is_active": False}
        )
    created = 0
    for payload in COURSES:
        values = {k: v for k, v in payload.items() if k not in {"slug", "instructor"}}
        _, made = Course.objects.get_or_create(
            slug=payload["slug"],
            defaults={
                **values,
                "branch": branch,
                "instructor": instructors[payload["instructor"]],
                "is_active": False,
            },
        )
        created += int(made)
    if stdout is not None:
        stdout.write(f"  + {created} courses (inactive until reviewed)")
    return created
