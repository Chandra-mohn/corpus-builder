from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def mirror_clone(repo_id: str, clone_url: str, mirror_dir: Path) -> Path:
    target = mirror_dir / f"{repo_id}.git"
    if target.exists():
        log.debug("Mirror already exists: %s", target)
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    log.info("Cloning mirror: %s -> %s", clone_url, target)
    subprocess.run(
        ["git", "clone", "--mirror", clone_url, str(target)],
        check=True,
    )
    return target
