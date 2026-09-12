"""Catalogue admin — where staff actually manage the menu."""

from __future__ import annotations

from typing import Any

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html

from apps.catalog.models import (
    AvailabilityWindow,
    Category,
    DietaryTag,
    MenuItem,
    MenuItemImage,
    Modifier,
    ModifierGroup,
    Variant,
    WishlistItem,
)
from apps.common.admin import money_column


@admin.register(DietaryTag)
class DietaryTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "is_allergen", "display_order")
    list_editable = ("display_order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("__str__", "branch", "item_count", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    list_filter = ("branch", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Items")
    def item_count(self, obj: Category) -> int:
        return obj.items.filter(is_active=True).count()


class MenuItemImageInline(admin.TabularInline):
    model = MenuItemImage
    extra = 1


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0
    fields = ("name", "price_delta", "is_default", "display_order", "is_active")


class ModifierInline(admin.TabularInline):
    model = Modifier
    extra = 1
    fields = ("name", "price_delta", "is_default", "is_available", "display_order")


class AvailabilityWindowInline(admin.TabularInline):
    model = AvailabilityWindow
    extra = 0
    verbose_name_plural = "Availability windows (leave empty for always available)"


@admin.register(ModifierGroup)
class ModifierGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "item", "min_select", "max_select", "modifier_count")
    list_filter = ("item__category",)
    search_fields = ("name", "item__name")
    inlines = [ModifierInline]

    @admin.display(description="Options")
    def modifier_count(self, obj: ModifierGroup) -> int:
        return obj.modifiers.count()


class ModifierGroupInline(admin.TabularInline):
    model = ModifierGroup
    extra = 0
    fields = ("name", "min_select", "max_select", "display_order")
    show_change_link = True


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price_display",
        "repricing_flag",
        "is_available_now",
        "is_featured",
        "is_active",
    )
    list_filter = ("needs_repricing", "is_active", "is_available_now", "is_featured", "category")
    list_editable = ("is_available_now", "is_featured")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("dietary_tags",)
    inlines = [MenuItemImageInline, VariantInline, ModifierGroupInline, AvailabilityWindowInline]
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "average_rating",
        "review_count",
        "order_count",
        "published_at",
    )
    actions = ["mark_repriced", "mark_unavailable", "mark_available"]

    fieldsets = (
        (None, {"fields": ("id", "branch", "category", "name", "slug", "description")}),
        (
            "Pricing",
            {
                "fields": ("base_price", "compare_at_price", "needs_repricing", "tax_class"),
                "description": (
                    "<strong>Prices are in kobo.</strong> ₦1,250.00 is entered as 125000.<br>"
                    "An item with <em>needs repricing</em> set is hidden from customers "
                    "and blocks deployment."
                ),
            },
        ),
        ("Kitchen", {"fields": ("prep_time_minutes", "is_available_now")}),
        ("Dietary", {"fields": ("dietary_tags", "allergen_note", "calories")}),
        ("Display", {"fields": ("is_featured", "display_order", "is_active")}),
        (
            "Statistics",
            {
                "fields": ("average_rating", "review_count", "order_count", "published_at"),
                "classes": ("collapse",),
                "description": "Calculated automatically. Not editable.",
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    price_display = money_column("base_price", "Price")

    @admin.display(description="Price status")
    def repricing_flag(self, obj: MenuItem) -> Any:
        if obj.needs_repricing:
            return format_html(
                '<span style="color:{};font-weight:700">{}</span>', "#b00020", "⚠ PLACEHOLDER"
            )
        return format_html('<span style="color:{}">{}</span>', "#0a7d28", "✓ confirmed")

    def changelist_view(
        self, request: HttpRequest, extra_context: dict[str, Any] | None = None
    ) -> HttpResponse:
        """Surface unpriced items on every visit to this page.

        The seeded prices are the frontend's dollar figures wearing a naira sign.
        Nobody should be able to browse this list without being told.
        """
        pending = MenuItem.objects.filter(is_active=True, needs_repricing=True).count()
        if pending:
            messages.warning(
                request,
                f"{pending} active item(s) still have PLACEHOLDER prices. They are hidden "
                "from customers and will block deployment. Set a real naira price, then "
                "clear “needs repricing” (there is a bulk action for this).",
            )
        return super().changelist_view(request, extra_context)

    @admin.action(description="Mark selected as repriced (base AND option prices confirmed)")
    def mark_repriced(self, request: HttpRequest, queryset: QuerySet[MenuItem]) -> None:
        """Clear the placeholder flag.

        Clearing it confirms the base price **and** every variant and modifier
        price on the item — options have no separate flag, they are covered by
        the item's. All of them are in kobo: ₦300.00 is entered as 30000.
        """
        still_zero = queryset.filter(base_price=0).count()
        if still_zero:
            self.message_user(
                request,
                f"{still_zero} item(s) still have a price of ₦0.00 and were skipped.",
                level=messages.ERROR,
            )
            queryset = queryset.exclude(base_price=0)
        updated = queryset.update(needs_repricing=False)
        self.message_user(request, f"{updated} item(s) marked as repriced.")

    @admin.action(description="86 selected (mark unavailable now)")
    def mark_unavailable(self, request: HttpRequest, queryset: QuerySet[MenuItem]) -> None:
        updated = queryset.update(is_available_now=False)
        self.message_user(request, f"{updated} item(s) marked unavailable.")

    @admin.action(description="Mark selected available again")
    def mark_available(self, request: HttpRequest, queryset: QuerySet[MenuItem]) -> None:
        updated = queryset.update(is_available_now=True)
        self.message_user(request, f"{updated} item(s) marked available.")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    """Read-only. Useful for spotting what customers want but cannot get."""

    list_display = ("user", "menu_item", "created_at")
    list_filter = ("menu_item__category",)
    search_fields = ("user__email", "menu_item__name")
    date_hierarchy = "created_at"
    readonly_fields = ("id", "user", "menu_item", "created_at", "updated_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False
