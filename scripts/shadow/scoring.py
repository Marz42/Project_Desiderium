"""Shadow validation scoring — compatibility layer over application domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.domain.trend_metrics import (
    Tier,
)
from app.domain.trend_metrics import (
    assign_age_bucket as _assign_age_bucket,
)
from app.domain.trend_metrics import (
    breakout_ratio as _breakout_ratio,
)
from app.domain.trend_metrics import (
    cold_start_velocity as _cold_start_velocity,
)
from app.domain.trend_metrics import (
    compute_channel_baselines as _compute_channel_baselines,
)
from app.domain.trend_metrics import (
    global_baseline_by_bucket as _global_baseline_by_bucket,
)
from app.domain.trend_metrics import (
    parse_iso_datetime as _parse_iso_datetime,
)
from app.domain.trend_metrics import (
    score_trend_cluster as _score_trend_cluster,
)
from app.services.scoring_config import get_scoring_config

AgeBucket = Literal["0_6h", "6_24h", "24_72h", "3_7d", "7d_plus"]

_cfg = get_scoring_config()
EPSILON = _cfg.epsilon
MIN_AGE_HOURS = _cfg.min_age_hours
BASELINE_SAMPLE_SIZE = _cfg.baselines.sample_size
CAPPED_BREAKOUT = _cfg.capped_breakout_max

# Public compatibility aliases used by Stage 1 scripts and tests.
assign_age_bucket = _assign_age_bucket
cold_start_velocity = _cold_start_velocity
parse_iso_datetime = _parse_iso_datetime
score_trend_cluster = _score_trend_cluster

TIER_WEIGHTS: dict[Tier, float] = {
    "priority": _cfg.channels.priority,
    "general": _cfg.channels.general,
    "experimental": _cfg.channels.experimental,
}


@dataclass(frozen=True)
class VideoRecord:
    video_id: str
    channel_id: str
    channel_name: str
    title: str
    published_at: datetime
    views: int
    likes: int | None
    comments: int | None
    duration_seconds: int
    language: str | None = None
    tier: Tier = "priority"
    url: str = ""

    @property
    def channel_external_id(self) -> str:
        return self.channel_id

    @property
    def content_item_id(self) -> str:
        return self.video_id


def compute_channel_baselines(videos, *, now=None, sample_size=BASELINE_SAMPLE_SIZE):
    cfg = get_scoring_config()
    if sample_size != cfg.baselines.sample_size:
        from dataclasses import replace

        cfg = replace(cfg, baselines=replace(cfg.baselines, sample_size=sample_size))
    return _compute_channel_baselines(videos, now=now, config=cfg)


def global_baseline_by_bucket(videos, *, now=None):
    return _global_baseline_by_bucket(videos, now=now)


def breakout_ratio(video, baselines, global_fallback, *, now=None):
    return _breakout_ratio(video, baselines, global_fallback, now=now)


def parse_duration_seconds(iso_duration: str) -> int:
    if not iso_duration.startswith("PT"):
        return 0
    duration = iso_duration[2:]
    hours = minutes = seconds = 0
    number = ""
    for char in duration:
        if char.isdigit():
            number += char
            continue
        if not number:
            continue
        if char == "H":
            hours = int(number)
        elif char == "M":
            minutes = int(number)
        elif char == "S":
            seconds = int(number)
        number = ""
    return hours * 3600 + minutes * 60 + seconds
