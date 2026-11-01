"""Settings loaded from the environment (names match .env.example).

The real key never appears in repr/str: ``model_api_key`` is a ``repr=False`` field.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

STANDARD_SPARK = "muse-spark-1.3"
CONTRIBUTOR_SPARK = "muse-spark-1.3-contributor"
SPARK_STAGES = {"navigator", "seer", "comparator", "fixer", "reaudit", "auditor"}


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    model_api_key: str = field(default="", repr=False)
    meta_api_base: str = "https://api.meta.ai/v1"
    model: str = CONTRIBUTOR_SPARK
    judge_model: str = STANDARD_SPARK
    judge_fallback_model: str = STANDARD_SPARK  # used when the judge model errors (D6: any Wonder error falls back to Spark)
    eval_model: str = CONTRIBUTOR_SPARK
    voice_model: str = "muse-voice-transcribe-1.0"
    private: bool = False
    run_timeout_s: int = 900  # a run that outlives this is failed; spec §15 caps a run at 15 min; a live purchase run takes ~9.5
    data_dir: Path = Path("./data")
    gcs_bucket: str = ""
    index_path: Path = Path("./data/index.db")
    cache_dir: Path = Path("./cache")
    replay_dir: Path = Path("./fixtures/replay")
    eval_dir: Path = Path("./eval/results")  # latest.json + public.json, served by GET /api/eval
    port: int = 8080
    default_mode: str = "replay"
    live_enabled: bool = True
    live_per_ip_per_hour: int = 3
    live_global_per_day: int = 40
    live_target_origins: str = "self"
    replay_keep: int = 20  # Replay copies kept (evicted oldest-first when a Replay starts and at boot); boot loads each kept copy once
    replay_min_age_s: int = 7200  # beyond the cap, only copies older than this are evicted: a judge still reviewing one must not lose it
    trust_proxy: bool = False  # behind Cloud Run the visitor is the first X-Forwarded-For hop; a direct client's header is ignored
    log_level: str = "info"

    def model_for(self, stage: str) -> str:
        """The only place a pipeline stage learns which model ID to call."""
        if stage == "voice":
            return self.voice_model
        if stage == "judge":
            chosen = self.judge_model
        elif stage == "judge_fallback":
            chosen = self.judge_fallback_model
        else:
            chosen = self.model
        if self.private and chosen.endswith("-contributor"):
            return STANDARD_SPARK
        return chosen

    @property
    def has_key(self) -> bool:
        return bool(self.model_api_key) and not self.model_api_key.startswith("REPLACE")


def load_settings(env: Mapping[str, str] | None = None, dotenv_path: Path | None = Path(".env")) -> Settings:
    """Build Settings. With ``env`` given, only that mapping is read (tests).

    Without it, ``.env`` values are merged under ``os.environ`` (the environment wins).
    """
    if env is None:
        merged: dict[str, str] = {}
        if dotenv_path and dotenv_path.exists():
            merged.update({k: v for k, v in dotenv_values(dotenv_path).items() if v is not None})
        merged.update(os.environ)
        env = merged

    def get(name: str, default: str) -> str:
        value = env.get(name)
        return default if value is None or value == "" else value

    return Settings(
        model_api_key=env.get("MODEL_API_KEY", ""),
        meta_api_base=get("META_API_BASE", Settings.meta_api_base),
        model=get("PARITY_MODEL", Settings.model),
        judge_model=get("PARITY_JUDGE_MODEL", Settings.judge_model),
        judge_fallback_model=get("PARITY_JUDGE_FALLBACK_MODEL", Settings.judge_fallback_model),
        eval_model=get("PARITY_EVAL_MODEL", Settings.eval_model),
        voice_model=get("PARITY_VOICE_MODEL", Settings.voice_model),
        private=_bool(get("PARITY_PRIVATE", "false")),
        eval_dir=Path(get("PARITY_EVAL_DIR", str(Settings.eval_dir))),
        run_timeout_s=int(get("PARITY_RUN_TIMEOUT_S", str(Settings.run_timeout_s))),
        data_dir=Path(get("PARITY_DATA_DIR", str(Settings.data_dir))),
        gcs_bucket=get("PARITY_GCS_BUCKET", ""),
        index_path=Path(get("PARITY_INDEX_PATH", str(Settings.index_path))),
        cache_dir=Path(get("PARITY_CACHE_DIR", str(Settings.cache_dir))),
        replay_dir=Path(get("PARITY_REPLAY_DIR", str(Settings.replay_dir))),
        port=int(get("PORT", str(Settings.port))),
        default_mode=get("PARITY_DEFAULT_MODE", Settings.default_mode),
        live_enabled=_bool(get("PARITY_LIVE_ENABLED", "true")),
        live_per_ip_per_hour=int(get("PARITY_LIVE_PER_IP_PER_HOUR", "3")),
        live_global_per_day=int(get("PARITY_LIVE_GLOBAL_PER_DAY", "40")),
        trust_proxy=_bool(get("PARITY_TRUST_PROXY", "0")),
        replay_keep=int(get("PARITY_REPLAY_KEEP", str(Settings.replay_keep))),
        replay_min_age_s=int(get("PARITY_REPLAY_MIN_AGE_S", str(Settings.replay_min_age_s))),
        live_target_origins=get("PARITY_LIVE_TARGET_ORIGINS", "self"),
        log_level=get("LOG_LEVEL", "info"),
    )
