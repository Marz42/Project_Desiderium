"""Unit tests for watchlist CSV validation."""

from app.schemas.watchlist import parse_csv_content, parse_csv_row


SAMPLE_CSV = """type,platform,name,url_or_id,tier,tags,note,enabled
channel,youtube,Test Channel,UCgR3SrM8T6GCFUTuxSFlR7A,priority,"anime,recap",note,true
keyword,youtube,anime recap,,general,search,generic,true
"""


def test_parse_valid_csv():
    result = parse_csv_content(SAMPLE_CSV)
    assert not any("missing required" in e for e in result.errors)
    assert result.imported == 2
    assert len(result.rows) == 2
    assert result.rows[0].data is not None
    assert result.rows[0].data.name == "Test Channel"
    assert result.rows[1].data.external_id == "anime recap"


def test_parse_invalid_type():
    row = parse_csv_row(
        {
            "type": "invalid",
            "platform": "youtube",
            "name": "X",
            "url_or_id": "test",
            "tier": "general",
            "tags": "",
            "note": "",
            "enabled": "true",
        },
        2,
    )
    assert row.errors
    assert row.data is None


def test_parse_missing_channel_url():
    row = parse_csv_row(
        {
            "type": "channel",
            "platform": "youtube",
            "name": "No URL",
            "url_or_id": "",
            "tier": "general",
            "tags": "",
            "note": "",
            "enabled": "true",
        },
        3,
    )
    assert "url_or_id is required" in row.errors[0]


def test_csv_watchlist_limit():
    rows = ["type,platform,name,url_or_id,tier,tags,note,enabled"]
    for i in range(5):
        rows.append(f"keyword,youtube,term{i},term{i},general,,,true")
    result = parse_csv_content("\n".join(rows), existing_count=98)
    assert result.imported == 2
    assert any("limit" in e for e in result.errors)
