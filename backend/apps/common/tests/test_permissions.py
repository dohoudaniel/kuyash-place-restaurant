"""Permission tests.

Today the frontend leaves /account, /orders and /wishlist entirely public and
shows fabricated data. These are the rules that replace that.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser, Group
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.common.permissions import (
    GROUP_KITCHEN,
    GROUP_MANAGERS,
    IsKitchenStaff,
    IsManager,
    IsOwnerOrStaff,
    IsStaffMember,
    in_group,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def factory() -> APIRequestFactory:
    return APIRequestFactory()


def make_user(email: str, *groups: str, **flags: object) -> User:
    user = User.objects.create_user(email=email, password="s3cret-pass-phrase", **flags)
    for name in groups:
        user.groups.add(Group.objects.get_or_create(name=name)[0])
    return user


def request_as(factory: APIRequestFactory, user: object, **headers: str):  # type: ignore[no-untyped-def]
    request = factory.get("/", **headers)
    request.user = user
    return request


def test_in_group_is_false_for_anonymous() -> None:
    assert in_group(AnonymousUser(), GROUP_KITCHEN) is False
    assert in_group(None, GROUP_KITCHEN) is False


def test_superuser_passes_every_group_check() -> None:
    admin = User.objects.create_superuser(email="a@example.com", password="s3cret-pass-phrase")
    assert in_group(admin, GROUP_KITCHEN) is True


def test_kitchen_permission(factory: APIRequestFactory) -> None:
    kitchen = make_user("kitchen@example.com", GROUP_KITCHEN)
    customer = make_user("customer@example.com")
    assert IsKitchenStaff().has_permission(request_as(factory, kitchen), None) is True
    assert IsKitchenStaff().has_permission(request_as(factory, customer), None) is False
    assert IsKitchenStaff().has_permission(request_as(factory, AnonymousUser()), None) is False


def test_manager_permission(factory: APIRequestFactory) -> None:
    manager = make_user("manager@example.com", GROUP_MANAGERS)
    kitchen = make_user("k@example.com", GROUP_KITCHEN)
    assert IsManager().has_permission(request_as(factory, manager), None) is True
    assert IsManager().has_permission(request_as(factory, kitchen), None) is False


def test_managers_also_satisfy_kitchen_access(factory: APIRequestFactory) -> None:
    """A manager must be able to run the pass on a short-staffed evening."""
    manager = make_user("manager@example.com", GROUP_MANAGERS)
    assert IsKitchenStaff().has_permission(request_as(factory, manager), None) is True


def test_staff_member_permission(factory: APIRequestFactory) -> None:
    staff = make_user("s@example.com", GROUP_KITCHEN)
    outsider = make_user("o@example.com")
    assert IsStaffMember().has_permission(request_as(factory, staff), None) is True
    assert IsStaffMember().has_permission(request_as(factory, outsider), None) is False


def test_owner_can_read_their_own_object(factory: APIRequestFactory) -> None:
    owner = make_user("owner@example.com")
    obj = SimpleNamespace(user=owner, guest_token="")
    assert IsOwnerOrStaff().has_object_permission(request_as(factory, owner), None, obj) is True


def test_another_user_cannot_read_it(factory: APIRequestFactory) -> None:
    owner = make_user("owner@example.com")
    intruder = make_user("intruder@example.com")
    obj = SimpleNamespace(user=owner, guest_token="")
    assert IsOwnerOrStaff().has_object_permission(request_as(factory, intruder), None, obj) is False


def test_staff_can_read_any_object(factory: APIRequestFactory) -> None:
    owner = make_user("owner@example.com")
    manager = make_user("manager@example.com", GROUP_MANAGERS)
    obj = SimpleNamespace(user=owner, guest_token="")
    assert IsOwnerOrStaff().has_object_permission(request_as(factory, manager), None, obj) is True


def test_guest_token_grants_access_to_its_own_object(factory: APIRequestFactory) -> None:
    obj = SimpleNamespace(user=None, guest_token="correct-token")
    request = request_as(factory, AnonymousUser(), HTTP_X_GUEST_TOKEN="correct-token")
    assert IsOwnerOrStaff().has_object_permission(request, None, obj) is True


def test_wrong_guest_token_is_refused(factory: APIRequestFactory) -> None:
    obj = SimpleNamespace(user=None, guest_token="correct-token")
    request = request_as(factory, AnonymousUser(), HTTP_X_GUEST_TOKEN="wrong-token")
    assert IsOwnerOrStaff().has_object_permission(request, None, obj) is False


def test_missing_guest_token_is_refused(factory: APIRequestFactory) -> None:
    obj = SimpleNamespace(user=None, guest_token="correct-token")
    assert (
        IsOwnerOrStaff().has_object_permission(request_as(factory, AnonymousUser()), None, obj)
        is False
    )


def test_empty_guest_token_on_the_object_grants_nothing(factory: APIRequestFactory) -> None:
    """An object with no token must not be unlocked by sending an empty header."""
    obj = SimpleNamespace(user=None, guest_token="")
    request = request_as(factory, AnonymousUser(), HTTP_X_GUEST_TOKEN="")
    assert IsOwnerOrStaff().has_object_permission(request, None, obj) is False
