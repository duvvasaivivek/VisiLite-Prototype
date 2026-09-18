from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import settings


DANGEROUS_SCHEMES = {"javascript", "file", "data", "vbscript"}


def host_allowed(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme in DANGEROUS_SCHEMES:
        return False
    if scheme and scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host in settings.allowed_domain_list:
        return True
    if settings.allow_external_navigation:
        return True
    return False


def assert_allowed(url: str) -> tuple[bool, str]:
    parsed = urlparse(url or "")
    if (parsed.scheme or "").lower() in DANGEROUS_SCHEMES:
        return False, f"Blocked dangerous protocol: {parsed.scheme}"
    if not host_allowed(url):
        return False, f"Unknown or unauthorized domain blocked: {parsed.hostname or url}"
    return True, "Domain allowed"
