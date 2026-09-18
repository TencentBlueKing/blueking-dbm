# -*- coding: utf-8 -*-
from unittest.mock import patch

from backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage import (
    _parse_drs_is_master_ok,
    _probe_drs_login,
    _probe_gse_alive,
)


class TestParseDrsIsMasterOk:
    def test_plain_one(self):
        assert _parse_drs_is_master_ok("1") == 1.0

    def test_numeric_types(self):
        assert _parse_drs_is_master_ok(1) == 1.0
        assert _parse_drs_is_master_ok(1.0) == 1.0

    def test_wrapped_connect_disconnect(self):
        payload = "connect to server 127.0.0.1:27017\n1\ndisconnect.\n"
        assert _parse_drs_is_master_ok(payload) == 1.0

    def test_non_one_is_parsed(self):
        assert _parse_drs_is_master_ok("0") == 0.0

    def test_garbage_returns_none(self):
        assert _parse_drs_is_master_ok("not a number") is None
        assert _parse_drs_is_master_ok(None) is None
        assert _parse_drs_is_master_ok("") is None


class TestProbeDrsLogin:
    def test_wrapped_ok_is_success(self):
        with patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage.MongoUtil"
        ) as mongo_util, patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage.DRSApi"
        ) as drs_api:
            mongo_util.get_mongodb_DRS_args_direct.return_value = {}
            drs_api.mongodb_rpc.return_value = "connect to server 127.0.0.1:27001\n1\ndisconnect.\n"
            drs_ok, auth_err = _probe_drs_login(1, "127.0.0.1", [27001])
        assert drs_ok is True
        assert auth_err is False

    def test_ok_not_one_is_failure(self):
        with patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage.MongoUtil"
        ) as mongo_util, patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage.DRSApi"
        ) as drs_api:
            mongo_util.get_mongodb_DRS_args_direct.return_value = {}
            drs_api.mongodb_rpc.return_value = "0"
            drs_ok, auth_err = _probe_drs_login(1, "127.0.0.1", [27001])
        assert drs_ok is False
        assert auth_err is False


class TestProbeGseAliveRetry:
    def test_retries_on_none_then_returns_true(self):
        with patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage._probe_gse_alive_once",
            side_effect=[None, True],
        ) as once, patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage.time.sleep"
        ) as sleep:
            assert _probe_gse_alive("127.0.0.1", 0) is True
        assert once.call_count == 2
        sleep.assert_called_once()

    def test_false_returns_without_retry(self):
        with patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage._probe_gse_alive_once",
            return_value=False,
        ) as once, patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage.time.sleep"
        ) as sleep:
            assert _probe_gse_alive("127.0.0.1", 0) is False
        assert once.call_count == 1
        sleep.assert_not_called()
