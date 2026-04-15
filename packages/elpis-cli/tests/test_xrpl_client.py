"""Tests for elpis_cli.xrpl_client module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from elpis_cli.xrpl_client import register_did_testnet


class TestRegisterDidTestnet:
    """Test XRPL Testnet full identity chain."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    @patch("httpx.AsyncClient")
    def test_faucet_failure_returns_error(self, MockClient):
        """All faucet retries fail -> result with error."""
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.post = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = self._run(register_did_testnet("did:xrpl:t#f", "aa"))
        assert result is not None
        assert result["registered"] is False
        assert "Faucet" in result.get("error", "")

    @patch("httpx.AsyncClient")
    def test_full_chain_success(self, MockClient):
        """Successful flow: faucet -> DIDSet -> MPT -> Credential."""
        async def mock_post(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()

            if "faucet" in url:
                resp.json.return_value = {
                    "account": {"address": "rTestAddr", "secret": "sSecret"}
                }
            else:
                body = kwargs.get("json", {})
                method = body.get("method", "")
                if method == "account_info":
                    resp.json.return_value = {
                        "result": {"account_data": {"Account": "rTestAddr", "Sequence": 10}}
                    }
                elif method == "submit":
                    resp.json.return_value = {
                        "result": {
                            "engine_result": "tesSUCCESS",
                            "tx_json": {"hash": "ABCDEF1234567890"},
                        }
                    }
                else:
                    resp.json.return_value = {"result": {}}
            return resp

        mock_client = AsyncMock()
        mock_client.post = mock_post
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = self._run(register_did_testnet("did:xrpl:t#f", "aabb", "Test"))
        assert result is not None
        assert result["registered"] is True
        assert result["address"] == "rTestAddr"
        assert result["steps"]["didset"]["success"] is True
        assert result["steps"]["mpt"]["success"] is True
        assert result["steps"]["credential"]["success"] is True

    @patch("httpx.AsyncClient")
    def test_partial_failure(self, MockClient):
        """DIDSet succeeds but MPT/Credential fail -> registered=True."""
        submit_count = 0

        async def mock_post(url, **kwargs):
            nonlocal submit_count
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()

            if "faucet" in url:
                resp.json.return_value = {
                    "account": {"address": "rAddr", "secret": "sSec"}
                }
            else:
                body = kwargs.get("json", {})
                method = body.get("method", "")
                if method == "account_info":
                    resp.json.return_value = {
                        "result": {"account_data": {"Sequence": 5}}
                    }
                elif method == "submit":
                    submit_count += 1
                    if submit_count == 1:
                        resp.json.return_value = {
                            "result": {"engine_result": "tesSUCCESS", "tx_json": {"hash": "DID123"}}
                        }
                    else:
                        resp.json.return_value = {
                            "result": {"engine_result": "tecNO_PERMISSION", "engine_result_message": "No"}
                        }
            return resp

        mock_client = AsyncMock()
        mock_client.post = mock_post
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = self._run(register_did_testnet("did:xrpl:t#f", "aa"))
        assert result["registered"] is True
        assert result["steps"]["didset"]["success"] is True
        assert result["steps"]["mpt"]["success"] is False

    @patch("httpx.AsyncClient")
    def test_exception_returns_none(self, MockClient):
        MockClient.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("network down")
        )
        result = self._run(register_did_testnet("did:xrpl:t#f", "aa"))
        assert result is None
