"""Academy routes."""

from __future__ import annotations

from django.urls import path

from apps.academy.views import (
    CertificateView,
    CourseCohortsView,
    CourseDetailView,
    CourseListView,
    EnrolmentCreateView,
    EnrolmentDetailView,
    EnrolmentPaymentVerifyView,
    EnrolmentPayView,
    MyEnrolmentsView,
)

app_name = "academy"

urlpatterns = [
    path("courses/", CourseListView.as_view(), name="courses"),
    path("courses/<slug:slug>/", CourseDetailView.as_view(), name="course-detail"),
    path("courses/<slug:slug>/cohorts/", CourseCohortsView.as_view(), name="course-cohorts"),
    path("enrolments/", EnrolmentCreateView.as_view(), name="enrol"),
    path("enrolments/mine/", MyEnrolmentsView.as_view(), name="my-enrolments"),
    path("enrolments/<str:reference>/", EnrolmentDetailView.as_view(), name="enrolment"),
    path("enrolments/<str:reference>/pay/", EnrolmentPayView.as_view(), name="enrolment-pay"),
    path(
        "enrolments/<str:reference>/certificate/",
        CertificateView.as_view(),
        name="enrolment-certificate",
    ),
    path(
        "payments/verify/<str:reference>/",
        EnrolmentPaymentVerifyView.as_view(),
        name="payment-verify",
    ),
]
