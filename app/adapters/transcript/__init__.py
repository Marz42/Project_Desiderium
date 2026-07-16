"""Transcript acquisition adapters."""

from app.adapters.transcript.asr import AsrAdapter, NullAsrAdapter
from app.adapters.transcript.youtube_captions import YouTubeCaptionsFetcher

__all__ = ["AsrAdapter", "NullAsrAdapter", "YouTubeCaptionsFetcher"]
