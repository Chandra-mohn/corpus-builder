from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TRAINING_KEYWORDS = [
    "training", "tutorial", "exercise", "chapter", "course",
    "learn", "hello", "sample", "example", "practice",
]


@dataclass
class SourceConfig:
    enabled: bool = False
    token_env: str = ""
    query: str = ""
    max_repos: int = 0  # 0 = no limit


@dataclass
class EvaluateConfig:
    threshold: int = 30
    training_keywords: list[str] = field(default_factory=lambda: list(DEFAULT_TRAINING_KEYWORDS))
    dry_run: bool = False
    report_path: str = ""


@dataclass
class Config:
    output_dir: str = "cobol-corpus"
    log_level: str = "INFO"
    sources: dict[str, SourceConfig] = field(default_factory=dict)
    evaluate: EvaluateConfig = field(default_factory=EvaluateConfig)


def load_config(path: Path) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    sources = {}
    for name, src_raw in raw.get("sources", {}).items():
        sources[name] = SourceConfig(**src_raw)

    eval_raw = raw.get("evaluate", {})
    evaluate = EvaluateConfig(
        threshold=eval_raw.get("threshold", 30),
        training_keywords=eval_raw.get("training_keywords", list(DEFAULT_TRAINING_KEYWORDS)),
        dry_run=eval_raw.get("dry_run", False),
        report_path=eval_raw.get("report_path", ""),
    )

    return Config(
        output_dir=raw.get("corpus", {}).get("output_dir", "cobol-corpus"),
        log_level=raw.get("logging", {}).get("level", "INFO"),
        sources=sources,
        evaluate=evaluate,
    )
