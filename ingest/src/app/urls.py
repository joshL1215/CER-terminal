"""URL canonicalization for deduplicating articles across runs and feeds."""

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Query parameters that only track where a click came from, not which page it is.
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "cmpid"}
TRACKING_PREFIXES = ("utm_",)


def canonicalize_url(url: str) -> str:
    """Normalize a URL so the same article from different links hashes the same.

    Lowercases scheme and host, drops default ports, fragments, tracking query
    params, and trailing slashes, and sorts the remaining query params.
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if parts.port and not (
        (scheme == "http" and parts.port == 80) or (scheme == "https" and parts.port == 443)
    ):
        host = f"{host}:{parts.port}"

    query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS and not key.lower().startswith(TRACKING_PREFIXES)
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((scheme, host, path, urlencode(query), ""))


def url_hash(url: str) -> str:
    """sha256 hex digest of the canonical URL; stored as articles.url_hash."""
    return hashlib.sha256(canonicalize_url(url).encode("utf-8")).hexdigest()
