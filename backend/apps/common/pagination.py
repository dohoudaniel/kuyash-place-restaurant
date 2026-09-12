"""Pagination.

Two styles, chosen by what the collection *is*:

- :class:`CursorPagination` for append-only, time-ordered feeds (orders, ledger
  entries). A new row arriving mid-listing cannot shift page boundaries and
  duplicate or skip a record.
- :class:`PagePagination` for finite, user-sortable collections (the menu).
  Cursor pagination cannot be used here: it *imposes* its own ``ordering`` so a
  cursor stays monotonic, which silently overrides any sort the caller asked for.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from rest_framework import pagination
from rest_framework.response import Response


class CursorPagination(pagination.CursorPagination):
    """Stable pagination for append-only feeds."""

    page_size = 20
    page_size_query_param = "limit"
    max_page_size = 100
    ordering = "-created_at"
    cursor_query_param = "cursor"

    def get_paginated_response(self, data: Any) -> Response:
        return Response(
            OrderedDict(
                [
                    ("results", data),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                ]
            )
        )


class PagePagination(pagination.PageNumberPagination):
    """Pagination that respects the queryset's own ordering.

    Used wherever the caller chooses the sort. Emits the same envelope as the
    cursor paginator, plus a total ``count``.
    """

    page_size = 20
    page_size_query_param = "limit"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data: Any) -> Response:
        count = self.page.paginator.count if self.page is not None else 0
        return Response(
            OrderedDict(
                [
                    ("results", data),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("count", count),
                ]
            )
        )
