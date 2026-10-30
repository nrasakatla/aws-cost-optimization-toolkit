"""Provider interfaces.

A Provider produces an inventory of :class:`~costtk.models.Resource` objects.
The synthetic provider is the default and the only one used by the demo; the
boto3 providers implement the same interface but are read-only stubs/adapters
that must be explicitly opted into.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Account, Resource

PROVIDER_REGISTRY: dict[str, type[Provider]] = {}


class Provider(ABC):
    """Abstract source of AWS resource inventory."""

    name: str = "base"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "name", None):
            PROVIDER_REGISTRY[cls.name] = cls

    @abstractmethod
    def collect_accounts(self) -> list[Account]:
        """Return the set of accounts this provider can see."""

    @abstractmethod
    def collect_resources(self) -> list[Resource]:
        """Return all resources for recommendation analysis."""


def get_provider(name: str, **kwargs: object) -> Provider:
    if name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider '{name}'. Available: {sorted(PROVIDER_REGISTRY)}")
    return PROVIDER_REGISTRY[name](**kwargs)
