"""Context7 REST API client for querying live Odoo documentation.

Queries the Context7 service (https://context7.com) for Odoo documentation
snippets as a supplement to the static knowledge base. Degrades gracefully
when unconfigured (no API key) or when Context7 is unavailable.

Uses only stdlib modules (urllib.request, urllib.error, urllib.parse, json,
os, logging, dataclasses) -- no third-party dependencies.

Exports:
    Context7Config           -- frozen config dataclass (api_key, base_url, timeout)
    DocSnippet               -- frozen dataclass for a documentation result
    Context7Client           -- main client class with resolve + query
    build_context7_from_env  -- factory that reads CONTEXT7_API_KEY from env
    _context7_get            -- low-level HTTP GET helper (for testing)
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger("odoo-gen.context7")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Context7Config:
    """Immutable configuration for the Context7 REST API client.

    Attributes:
        api_key:  Bearer token for Context7 authentication (empty = unconfigured).
        base_url: Root URL for the Context7 v2 API.
        timeout:  HTTP request timeout in seconds.
    """

    api_key: str = ""
    base_url: str = "https://context7.com/api/v2"
    timeout: int = 10


@dataclass(frozen=True)
class DocSnippet:
    """A single documentation snippet returned by Context7.

    Attributes:
        title:      Snippet title (e.g. "Model Fields").
        content:    Snippet body text.
        source_url: Original documentation URL (may be empty).
    """

    title: str
    content: str
    source_url: str = ""


# ---------------------------------------------------------------------------
# Low-level HTTP helper
# ---------------------------------------------------------------------------

def _context7_get(url: str, api_key: str, timeout: int = 10) -> dict | list | None:
    """Perform an HTTP GET against a Context7 endpoint.

    Adds an ``Authorization: Bearer`` header when *api_key* is non-empty.
    Returns parsed JSON on success, or ``None`` on any network / parse error.

    Args:
        url:     Fully-qualified URL to GET.
        api_key: Bearer token (empty string skips auth header).
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON (dict or list), or None on failure.
    """
    request = urllib.request.Request(url)
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError,
            TimeoutError, OSError) as exc:
        logger.warning("Context7 GET %s failed: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class Context7Client:
    """REST client for the Context7 documentation service.

    When *config* has an empty ``api_key`` the client is considered
    unconfigured and all query methods return empty results without making
    any HTTP requests.

    Usage::

        client = Context7Client(Context7Config(api_key="..."))
        snippets = client.query_docs("how to define Many2one fields in Odoo")
    """

    def __init__(self, config: Context7Config | None = None) -> None:
        self._config: Context7Config = config if config is not None else Context7Config()
        self._odoo_library_id: str | None = None

    @property
    def is_configured(self) -> bool:
        """Return True when an API key is present."""
        return bool(self._config.api_key)

    # -- Library resolution ------------------------------------------------

    def resolve_odoo_library(self) -> str | None:
        """Resolve the Odoo library ID from Context7.

        The result is cached after the first successful lookup so that
        repeated calls do not hit the network.

        Returns:
            Library ID string, or None when unconfigured / on failure.
        """
        if self._odoo_library_id is not None:
            return self._odoo_library_id

        if not self.is_configured:
            return None

        search_query = urllib.parse.quote_plus("odoo framework development")
        url = (
            f"{self._config.base_url}/libs/search"
            f"?libraryName=odoo&query={search_query}"
        )

        data = _context7_get(url, self._config.api_key, self._config.timeout)
        if not isinstance(data, list) or len(data) == 0:
            logger.warning("Context7 library search returned no results")
            return None

        try:
            library_id = str(data[0]["id"])
        except (KeyError, IndexError, TypeError) as exc:
            logger.warning("Context7 library search response malformed: %s", exc)
            return None

        self._odoo_library_id = library_id
        return library_id

    # -- Documentation querying --------------------------------------------

    def query_docs(self, query: str) -> list[DocSnippet]:
        """Query Context7 for Odoo documentation snippets.

        Returns an empty list (never raises) when:
        - The client is unconfigured (no API key).
        - Library resolution fails.
        - The HTTP request fails or returns invalid data.

        Args:
            query: Natural-language search query.

        Returns:
            List of DocSnippet results (may be empty).
        """
        if not self.is_configured:
            return []

        try:
            library_id = self.resolve_odoo_library()
            if library_id is None:
                return []

            encoded_query = urllib.parse.quote_plus(query)
            url = (
                f"{self._config.base_url}/context"
                f"?libraryId={library_id}&query={encoded_query}"
            )

            data = _context7_get(url, self._config.api_key, self._config.timeout)
            if not isinstance(data, list):
                logger.warning("Context7 docs query returned non-list: %s", type(data))
                return []

            return [
                DocSnippet(
                    title=str(item.get("title", "")),
                    content=str(item.get("content", "")),
                    source_url=str(item.get("sourceUrl", "")),
                )
                for item in data
            ]

        except Exception as exc:
            logger.warning("Context7 query_docs error (degrading gracefully): %s", exc)
            return []


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_context7_from_env() -> Context7Client:
    """Build a Context7Client from the CONTEXT7_API_KEY environment variable.

    Returns an unconfigured client (no-op) when the variable is absent.
    Never raises.
    """
    api_key = os.environ.get("CONTEXT7_API_KEY", "")
    config = Context7Config(api_key=api_key)
    return Context7Client(config)
