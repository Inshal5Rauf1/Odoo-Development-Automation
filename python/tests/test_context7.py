"""Unit tests for Context7 REST API client (MCP-05 a-f).

Tests cover:
    a) Config defaults and frozen dataclass
    b) Client configured/unconfigured states
    c) Library resolution with caching
    d) Document querying (success + all failure modes)
    e) build_context7_from_env factory
    f) _context7_get helper auth header behavior
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(data: object) -> MagicMock:
    """Create a mock HTTP response that works as a context manager."""
    resp = MagicMock()
    resp.read.return_value = json.dumps(data).encode("utf-8")
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def configured_client():
    """Return a Context7Client with a dummy API key."""
    from odoo_gen_utils.context7 import Context7Client, Context7Config

    return Context7Client(Context7Config(api_key="test-key-123"))


@pytest.fixture()
def unconfigured_client():
    """Return a Context7Client with no API key (unconfigured)."""
    from odoo_gen_utils.context7 import Context7Client

    return Context7Client()


# ---------------------------------------------------------------------------
# MCP-05 a: Config defaults
# ---------------------------------------------------------------------------

class TestContext7Config:
    def test_context7_config_defaults(self):
        from odoo_gen_utils.context7 import Context7Config

        cfg = Context7Config()
        assert cfg.api_key == ""
        assert cfg.base_url == "https://context7.com/api/v2"
        assert cfg.timeout == 10

    def test_doc_snippet_frozen(self):
        from odoo_gen_utils.context7 import DocSnippet

        snippet = DocSnippet(title="T", content="C", source_url="http://x")
        with pytest.raises(AttributeError):
            snippet.title = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MCP-05 b: Client configured state
# ---------------------------------------------------------------------------

class TestClientConfigured:
    def test_client_not_configured_when_no_api_key(self, unconfigured_client):
        assert unconfigured_client.is_configured is False

    def test_client_configured_when_api_key_set(self, configured_client):
        assert configured_client.is_configured is True


# ---------------------------------------------------------------------------
# MCP-05 c: Library resolution
# ---------------------------------------------------------------------------

class TestResolveOdooLibrary:
    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_resolve_odoo_library_success(self, mock_urlopen, configured_client):
        mock_urlopen.return_value = _mock_response(
            [{"id": "lib-odoo-123", "name": "odoo", "description": "Odoo framework"}],
        )
        result = configured_client.resolve_odoo_library()
        assert result == "lib-odoo-123"
        mock_urlopen.assert_called_once()

    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_resolve_odoo_library_caches_result(self, mock_urlopen, configured_client):
        mock_urlopen.return_value = _mock_response(
            [{"id": "lib-odoo-123", "name": "odoo", "description": "Odoo framework"}],
        )
        first = configured_client.resolve_odoo_library()
        second = configured_client.resolve_odoo_library()
        assert first == second == "lib-odoo-123"
        # Only one HTTP call -- second was cached
        assert mock_urlopen.call_count == 1

    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_resolve_odoo_library_returns_none_on_http_error(
        self, mock_urlopen, configured_client,
    ):
        mock_urlopen.side_effect = URLError("connection refused")
        result = configured_client.resolve_odoo_library()
        assert result is None

    def test_resolve_odoo_library_returns_none_when_unconfigured(
        self, unconfigured_client,
    ):
        result = unconfigured_client.resolve_odoo_library()
        assert result is None


# ---------------------------------------------------------------------------
# MCP-05 d: Document querying
# ---------------------------------------------------------------------------

class TestQueryDocs:
    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_query_docs_success(self, mock_urlopen, configured_client):
        from odoo_gen_utils.context7 import DocSnippet

        # First call resolves library, second call fetches docs
        mock_urlopen.side_effect = [
            _mock_response([{"id": "lib-odoo-1", "name": "odoo", "description": ""}]),
            _mock_response([
                {
                    "title": "Model Fields",
                    "content": "Fields define...",
                    "sourceUrl": "https://docs.odoo.com/fields",
                },
                {
                    "title": "Views",
                    "content": "Views render...",
                    "sourceUrl": "https://docs.odoo.com/views",
                },
            ]),
        ]
        result = configured_client.query_docs("fields in odoo")
        assert len(result) == 2
        assert isinstance(result[0], DocSnippet)
        assert result[0].title == "Model Fields"
        assert result[0].content == "Fields define..."
        assert result[0].source_url == "https://docs.odoo.com/fields"
        assert result[1].title == "Views"

    def test_query_docs_unconfigured(self, unconfigured_client):
        result = unconfigured_client.query_docs("anything")
        assert result == []

    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_query_docs_http_error(self, mock_urlopen, configured_client):
        # First call resolves library OK, second raises HTTPError
        mock_urlopen.side_effect = [
            _mock_response([{"id": "lib-1", "name": "odoo", "description": ""}]),
            HTTPError(
                url="https://context7.com/api/v2/context",
                code=429,
                msg="Too Many Requests",
                hdrs=MagicMock(),  # type: ignore[arg-type]
                fp=None,
            ),
        ]
        result = configured_client.query_docs("rate limited")
        assert result == []

    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_query_docs_timeout(self, mock_urlopen, configured_client):
        # First call resolves library OK, second raises timeout
        mock_urlopen.side_effect = [
            _mock_response([{"id": "lib-1", "name": "odoo", "description": ""}]),
            TimeoutError("Connection timed out"),
        ]
        result = configured_client.query_docs("slow query")
        assert result == []

    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_query_docs_invalid_json(self, mock_urlopen, configured_client):
        # First call resolves library OK, second returns invalid JSON
        bad_resp = MagicMock()
        bad_resp.read.return_value = b"<html>not json</html>"
        bad_resp.__enter__ = lambda s: s
        bad_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.side_effect = [
            _mock_response([{"id": "lib-1", "name": "odoo", "description": ""}]),
            bad_resp,
        ]
        result = configured_client.query_docs("bad response")
        assert result == []


# ---------------------------------------------------------------------------
# MCP-05 e: Factory function
# ---------------------------------------------------------------------------

class TestBuildContext7FromEnv:
    def test_build_context7_from_env_with_key(self, monkeypatch):
        from odoo_gen_utils.context7 import build_context7_from_env

        monkeypatch.setenv("CONTEXT7_API_KEY", "my-secret-key")
        client = build_context7_from_env()
        assert client.is_configured is True

    def test_build_context7_from_env_without_key(self, monkeypatch):
        from odoo_gen_utils.context7 import build_context7_from_env

        monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)
        client = build_context7_from_env()
        assert client.is_configured is False


# ---------------------------------------------------------------------------
# MCP-05 f: _context7_get helper auth header
# ---------------------------------------------------------------------------

class TestContext7GetHelper:
    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_context7_get_helper_adds_auth_header(self, mock_urlopen):
        from odoo_gen_utils.context7 import _context7_get

        mock_urlopen.return_value = _mock_response({"ok": True})
        _context7_get("https://example.com/api", api_key="bearer-token-123")
        # Inspect the Request object passed to urlopen
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.get_header("Authorization") == "Bearer bearer-token-123"

    @patch("odoo_gen_utils.context7.urllib.request.urlopen")
    def test_context7_get_helper_no_header_when_no_key(self, mock_urlopen):
        from odoo_gen_utils.context7 import _context7_get

        mock_urlopen.return_value = _mock_response({"ok": True})
        _context7_get("https://example.com/api", api_key="")
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert not request.has_header("Authorization")
