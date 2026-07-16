"""Unit tests for rule-based trend clustering."""

from __future__ import annotations

from app.services.clustering import cluster_videos, match_entity


def test_match_entity_one_piece() -> None:
    match = match_entity("Luffy vs Gorosei - One Piece Egghead Recap")
    assert match is not None
    assert match.entity.entity_id == "trend_one_piece"


def test_cluster_requires_multiple_channels() -> None:
    videos = [
        {
            "content_item_id": "1",
            "channel_id": "ch-a",
            "title": "One Piece Egghead episode recap",
            "views": 1000,
            "capped_breakout": 2.5,
            "breakout_ratio": 2.5,
            "published_at": None,
        },
        {
            "content_item_id": "2",
            "channel_id": "ch-b",
            "title": "Luffy Egghead One Piece summary",
            "views": 2000,
            "capped_breakout": 3.0,
            "breakout_ratio": 3.0,
            "published_at": None,
        },
    ]
    clusters = cluster_videos(videos)
    assert "trend_one_piece" in clusters
    assert len(clusters["trend_one_piece"]) == 2


def test_single_channel_cluster_filtered() -> None:
    videos = [
        {
            "content_item_id": "1",
            "channel_id": "ch-a",
            "title": "Jujutsu Kaisen Gojo fight recap",
            "views": 1000,
            "capped_breakout": 4.0,
            "breakout_ratio": 4.0,
            "published_at": None,
        },
        {
            "content_item_id": "2",
            "channel_id": "ch-a",
            "title": "JJK Sukuna battle explained",
            "views": 2000,
            "capped_breakout": 3.0,
            "breakout_ratio": 3.0,
            "published_at": None,
        },
    ]
    clusters = cluster_videos(videos)
    assert "trend_jjk" not in clusters
