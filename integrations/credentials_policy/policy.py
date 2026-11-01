"""Credential safety policy: references are allowed, secrets are not."""
from __future__ import annotations

import re
from typing import Any


class CredentialPolicyError(ValueError):
    pass


SECRET_KEY = re.compile(r"(?:api[_-]?key|password|passwd|token|secret|private[_-]?key|credential|client_secret)", re.I)
SECRET_VALUE = re.compile(r"(?:sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9]{20,}|bearer\s+[A-Za-z0-9._-]{12,})", re.I)
REFERENCE = re.compile(r"^[a-z][a-z0-9_.-]{2,127}$")


def validate_credential_reference(reference: str) -> str:
    if not REFERENCE.fullmatch(reference or ""):
        raise CredentialPolicyError("credential_ref должен быть ссылкой, а не секретом")
    if SECRET_KEY.search(reference):
        raise CredentialPolicyError("credential_ref не должен содержать secret-like имя")
    return reference


def validate_no_secrets(value: Any, path: str = "value") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) != "credential_ref" and SECRET_KEY.search(str(key)):
                raise CredentialPolicyError(f"Секретное поле запрещено: {path}.{key}")
            validate_no_secrets(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            validate_no_secrets(item, f"{path}[{index}]")
    elif isinstance(value, str) and SECRET_VALUE.search(value):
        raise CredentialPolicyError(f"Похоже на секрет в {path}")


def safe_log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return only non-sensitive metadata suitable for an audit log."""
    validate_no_secrets(payload)
    return {key: value for key, value in payload.items() if not SECRET_KEY.search(key)}
