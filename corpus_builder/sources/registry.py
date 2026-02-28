from __future__ import annotations

import logging
import os
from typing import Callable

from ..config import SourceConfig
from .base import SourceAdapter

log = logging.getLogger(__name__)

AdapterFactory = Callable[[SourceConfig], SourceAdapter]

_REGISTRY: dict[str, AdapterFactory] = {}


def register_adapter(name: str, factory: AdapterFactory) -> None:
    _REGISTRY[name] = factory
    log.debug("Registered adapter: %s", name)


def get_adapter(name: str, config: SourceConfig) -> SourceAdapter | None:
    factory = _REGISTRY.get(name)
    if factory is None:
        log.warning("Unknown source adapter: %s", name)
        return None
    return factory(config)


def list_adapters() -> list[str]:
    return list(_REGISTRY.keys())


def _register_builtins() -> None:
    from .github import GitHubAdapter
    from .software_heritage import SoftwareHeritageAdapter

    register_adapter(
        "github",
        lambda cfg: GitHubAdapter(
            token=os.getenv(cfg.token_env, ""),
            query=cfg.query,
            max_repos=cfg.max_repos,
        ),
    )
    register_adapter(
        "software_heritage",
        lambda cfg: SoftwareHeritageAdapter(
            query=cfg.query,
            max_repos=cfg.max_repos,
        ),
    )


_register_builtins()
