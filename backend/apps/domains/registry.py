"""Domain registry — maps domain names to environment instances."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import ErayaEnvironment

_registry: dict[str, "ErayaEnvironment"] = {}


def register_domain(name: str, env: "ErayaEnvironment") -> None:
    _registry[name] = env


def get_domain(name: str) -> "ErayaEnvironment | None":
    return _registry.get(name)


def get_registered_domains() -> list[str]:
    return list(_registry.keys())


def _bootstrap_domains() -> None:
    from .telecom.adapter import TelecomEnvironment
    from .cloud.adapter import CloudEnvironment
    from .icu.adapter import ICUEnvironment

    register_domain("5g", TelecomEnvironment())
    register_domain("cloud", CloudEnvironment())
    register_domain("icu", ICUEnvironment())
