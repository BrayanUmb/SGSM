"""Application errors rendered as generic JSON (OWASP API8: no stack traces)."""


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def utc_now():
    """Naive UTC 'now' (timezone-aware API, naive value for ISO comparisons)."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)
