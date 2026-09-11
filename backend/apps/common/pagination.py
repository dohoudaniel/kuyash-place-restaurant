"""Pagination defaults."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from rest_framework import pagination
from rest_framework.response import Response


class CursorPagination(pagination.CursorPagination):
    """Cursor pagination keyed on creation time.

    Cursor rather than offset so that a new order arriving mid-listing cannot
    shift the page boundaries and duplicate or skip a row.
    """

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
