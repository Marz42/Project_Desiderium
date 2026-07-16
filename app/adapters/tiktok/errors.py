"""TikTok adapter error types."""


class TikTokError(RuntimeError):
    """Base error for TikTok scraping failures."""


class CookieExpiredError(TikTokError):
    """Raised when the TikTok session cookie is missing or expired."""


class TikTokScrapeError(TikTokError):
    """Raised when page structure cannot be parsed."""


class TikTokDisabledError(TikTokError):
    """Raised when TikTok adapter is disabled via configuration."""
