"""Support routes."""

from __future__ import annotations

from django.urls import path

from apps.support.chat_views import (
    ChatEscalateView,
    ChatMessageCreateView,
    ChatSessionCreateView,
    ChatSessionDetailView,
)
from apps.support.views import (
    ContactView,
    FaqListView,
    MyTicketsView,
    OpenTicketsView,
    TicketDetailView,
)

app_name = "support"

urlpatterns = [
    path("contact/", ContactView.as_view(), name="contact"),
    path("faq/", FaqListView.as_view(), name="faq"),
    path("chat/sessions/", ChatSessionCreateView.as_view(), name="chat-start"),
    path("chat/sessions/<uuid:session_id>/", ChatSessionDetailView.as_view(), name="chat-detail"),
    path(
        "chat/sessions/<uuid:session_id>/messages/",
        ChatMessageCreateView.as_view(),
        name="chat-messages",
    ),
    path(
        "chat/sessions/<uuid:session_id>/escalate/",
        ChatEscalateView.as_view(),
        name="chat-escalate",
    ),
    path("tickets/", MyTicketsView.as_view(), name="my-tickets"),
    path("tickets/open/", OpenTicketsView.as_view(), name="open-tickets"),
    path("tickets/<str:reference>/", TicketDetailView.as_view(), name="ticket-detail"),
]
