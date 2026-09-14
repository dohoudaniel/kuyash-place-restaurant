"""Encrypt MFA secrets at rest.

django-allauth's default adapter stores the TOTP secret and the recovery-code
seed **in the clear** ("this hook can be used to encrypt those"). Anyone with a
database dump could then mint valid second-factor codes for every staff member.
This adapter encrypts both with Fernet, keyed from ``SECRET_KEY``.

Consequence: rotating ``SECRET_KEY`` invalidates every enrolled authenticator.
Staff re-enrol on their next admin sign-in (a superuser can also reset one from
the user admin). See SECURITY.md.
"""

from __future__ import annotations

import base64
import hashlib

from allauth.mfa.adapter import DefaultMFAAdapter
from cryptography.fernet import Fernet
from django.conf import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(f"kuyash.mfa:{settings.SECRET_KEY}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


class KuyashMFAAdapter(DefaultMFAAdapter):
    def encrypt(self, text: str) -> str:
        return _fernet().encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        return _fernet().decrypt(encrypted_text.encode()).decode()
