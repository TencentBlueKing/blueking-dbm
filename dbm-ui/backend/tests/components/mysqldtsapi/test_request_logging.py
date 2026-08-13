# -*- coding: utf-8 -*-
"""MySQL DTS 写操作请求日志：嵌套密码脱敏与统一入口打点。"""
import copy
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.components.mysqldtsapi.client import _MySQLDTSApi
from backend.components.mysqldtsapi.log_context import get_flow_log_extra, reset_flow_log_extra, set_flow_log_extra
from backend.components.mysqldtsapi.redact import PASSWORD_PLACEHOLDER, redact_passwords
from backend.flow.plugins.components.collections.common.base_service import BaseService

SECRET = "plain-secret-do-not-log"


class RedactPasswordsTest(SimpleTestCase):
    def _nested_payload(self):
        return {
            "source": {
                "host": "127.0.0.2",
                "port": 3306,
                "user": "dts_u",
                "password": SECRET,
            },
            "task": {
                "target_config": {
                    "host": "127.0.0.3",
                    "user": "tgt_u",
                    "password": SECRET,
                    "spider": {
                        "tdbctl": {
                            "host": "127.0.0.4",
                            "user": "ctl_u",
                            "Password": SECRET,
                        },
                        "shards": [
                            {
                                "host": "127.0.0.5",
                                "user": "shard_u",
                                "password": SECRET,
                            }
                        ],
                    },
                }
            },
        }

    def test_nested_source_target_and_shard_passwords_are_redacted(self):
        original = self._nested_payload()
        redacted = redact_passwords(original)

        self.assertEqual(redacted["source"]["password"], PASSWORD_PLACEHOLDER)
        self.assertEqual(redacted["task"]["target_config"]["password"], PASSWORD_PLACEHOLDER)
        self.assertEqual(redacted["task"]["target_config"]["spider"]["tdbctl"]["Password"], PASSWORD_PLACEHOLDER)
        self.assertEqual(
            redacted["task"]["target_config"]["spider"]["shards"][0]["password"],
            PASSWORD_PLACEHOLDER,
        )
        self.assertEqual(redacted["source"]["host"], "127.0.0.2")
        self.assertEqual(redacted["source"]["user"], "dts_u")
        self.assertEqual(redacted["task"]["target_config"]["host"], "127.0.0.3")
        self.assertEqual(redacted["task"]["target_config"]["spider"]["shards"][0]["user"], "shard_u")
        self.assertNotIn(SECRET, str(redacted))

    def test_list_of_dicts_is_redacted(self):
        payload = [{"password": SECRET, "host": "127.0.0.2"}, {"PASSWORD": SECRET, "user": "u"}]
        redacted = redact_passwords(payload)
        self.assertEqual(redacted[0]["password"], PASSWORD_PLACEHOLDER)
        self.assertEqual(redacted[1]["PASSWORD"], PASSWORD_PLACEHOLDER)
        self.assertEqual(redacted[0]["host"], "127.0.0.2")
        self.assertEqual(redacted[1]["user"], "u")

    def test_no_password_returns_equal_copy_not_same_object(self):
        payload = {"host": "127.0.0.2", "user": "u", "nested": {"port": 3306}}
        snapshot = copy.deepcopy(payload)
        redacted = redact_passwords(payload)
        self.assertEqual(redacted, snapshot)
        self.assertIsNot(redacted, payload)
        self.assertIsNot(redacted["nested"], payload["nested"])
        self.assertEqual(payload, snapshot)

    def test_empty_and_none_do_not_raise(self):
        self.assertEqual(redact_passwords({}), {})
        self.assertIsNot(redact_passwords({}), {})
        self.assertIsNone(redact_passwords(None))
        self.assertEqual(redact_passwords(""), "")
        self.assertEqual(redact_passwords(0), 0)
        self.assertEqual(redact_passwords([]), [])
        self.assertIsNot(redact_passwords([]), [])


class WriteRequestLoggingTest(SimpleTestCase):
    def setUp(self):
        with patch("backend.components.mysqldtsapi.client.ProxyAPI"):
            self.api = _MySQLDTSApi()
        self.api._proxy_rpc = MagicMock(return_value={})

    def _call(self, method, url, params=None):
        return self.api._call("127.0.0.2:8261", method, url, params, bk_cloud_id=0)

    def test_create_source_logs_before_rpc_failure(self):
        self.api._proxy_rpc.side_effect = RuntimeError("dts down")
        params = {"source": {"host": "127.0.0.2", "user": "u", "password": SECRET}}
        with self.assertLogs("root", level="INFO") as cm:
            with self.assertRaises(RuntimeError):
                self._call("POST", "/api/v1/sources", params)
        joined = "\n".join(cm.output)
        self.assertIn("POST", joined)
        self.assertIn("/api/v1/sources", joined)
        self.assertIn(PASSWORD_PLACEHOLDER, joined)
        self.assertNotIn(SECRET, joined)
        self.assertNotIn("v2/mysql-dts/rpc", joined)

    def test_get_task_status_does_not_log_write_request(self):
        with patch("backend.components.mysqldtsapi.client.logging.getLogger") as mock_get:
            logger = MagicMock()
            mock_get.return_value = logger
            self._call("GET", "/api/v1/tasks/t1/status", {"source_name_list": ["s1"]})
            logger.info.assert_not_called()

    def test_create_task_nested_password_is_placeholder(self):
        params = {
            "task": {
                "target_config": {
                    "host": "127.0.0.3",
                    "user": "tgt",
                    "password": SECRET,
                }
            }
        }
        with self.assertLogs("root", level="INFO") as cm:
            self._call("POST", "/api/v1/tasks", params)
        joined = "\n".join(cm.output)
        self.assertIn(PASSWORD_PLACEHOLDER, joined)
        self.assertNotIn(SECRET, joined)
        self.assertIn("127.0.0.3", joined)

    def test_call_does_not_mutate_params(self):
        params = {"source": {"password": SECRET, "host": "127.0.0.2"}}
        snapshot = copy.deepcopy(params)
        with self.assertLogs("root", level="INFO"):
            self._call("POST", "/api/v1/sources", params)
        self.assertEqual(params, snapshot)

    def test_delete_and_put_log_get_list_and_cluster_do_not(self):
        with self.assertLogs("root", level="INFO") as writes:
            self._call("DELETE", "/api/v1/sources/s1", {"force": True})
            self._call("PUT", "/api/v1/cluster/info", {"name": "n"})
        joined = "\n".join(writes.output)
        self.assertIn("DELETE", joined)
        self.assertIn("PUT", joined)
        with patch("backend.components.mysqldtsapi.client.logging.getLogger") as mock_get:
            logger = MagicMock()
            mock_get.return_value = logger
            self._call("GET", "/api/v1/sources", {})
            self._call("GET", "/api/v1/tasks/t1/status", {})
            self._call("GET", "/api/v1/cluster/info", {})
            logger.info.assert_not_called()

    def test_newline_in_params_or_url_does_not_split_log_record(self):
        params = {"note": "line1\nline2", "password": "pw\nsecret"}
        with self.assertLogs("root", level="INFO") as cm:
            self._call("POST", "/api/v1/sources", params)
        for record in cm.records:
            self.assertNotIn("\n", record.getMessage())

    def test_log_dump_failure_does_not_block_rpc(self):
        with patch("backend.components.mysqldtsapi.client.json.dumps", side_effect=TypeError("boom")):
            self._call("POST", "/api/v1/sources", {"source": {"password": SECRET}})
        self.api._proxy_rpc.assert_called_once()

    def test_with_node_context_logs_only_to_flow(self):
        extra = {"root_id": "r1", "node_id": "n1", "version_id": "v1"}
        token = set_flow_log_extra(extra)
        try:
            with patch("backend.components.mysqldtsapi.client.logging.getLogger") as mock_get:
                flow_logger = MagicMock()
                root_logger = MagicMock()
                mock_get.side_effect = lambda name: flow_logger if name == "flow" else root_logger
                self._call("POST", "/api/v1/sources", {"password": SECRET})
                flow_logger.info.assert_called_once()
                root_logger.info.assert_not_called()
                _args, kwargs = flow_logger.info.call_args
                self.assertEqual(kwargs.get("extra"), extra)
                self.assertNotIn(SECRET, str(flow_logger.info.call_args))
                self.assertEqual(len(_args), 1)
                self.assertNotIn("%s", _args[0])
                self.assertIn("POST", _args[0])
                self.assertIn("/api/v1/sources", _args[0])
        finally:
            reset_flow_log_extra(token)

    def test_without_node_context_logs_only_to_root(self):
        with patch("backend.components.mysqldtsapi.client.logging.getLogger") as mock_get:
            flow_logger = MagicMock()
            root_logger = MagicMock()
            mock_get.side_effect = lambda name: flow_logger if name == "flow" else root_logger
            self._call("POST", "/api/v1/sources", {"password": SECRET})
            root_logger.info.assert_called_once()
            flow_logger.info.assert_not_called()

    def test_get_still_skips_when_node_context_present(self):
        extra = {"root_id": "r1", "node_id": "n1", "version_id": "v1"}
        token = set_flow_log_extra(extra)
        try:
            with patch("backend.components.mysqldtsapi.client.logging.getLogger") as mock_get:
                logger = MagicMock()
                mock_get.return_value = logger
                self._call("GET", "/api/v1/tasks/t1/status", {})
                logger.info.assert_not_called()
        finally:
            reset_flow_log_extra(token)


class FlowLogContextServiceTest(SimpleTestCase):
    def _data(self):
        data = MagicMock()
        data.get_one_of_inputs.return_value = {}
        return data

    def test_execute_error_clears_node_context(self):
        seen = {}

        class BoomService(BaseService):
            def _execute(self, data, parent_data):
                seen["extra"] = get_flow_log_extra()
                raise RuntimeError("boom")

        svc = BoomService()
        svc._runtime_attrs = {"root_pipeline_id": "r1", "id": "n1", "version": "v1"}
        self.assertIsNone(get_flow_log_extra())
        self.assertFalse(svc.execute(self._data(), None))
        self.assertIsNotNone(seen.get("extra"))
        self.assertEqual(seen["extra"]["node_id"], "n1")
        self.assertIsNone(get_flow_log_extra())

    def test_schedule_error_clears_node_context(self):
        seen = {}

        class BoomService(BaseService):
            def _execute(self, data, parent_data):
                return True

            def _schedule(self, data, parent_data, callback_data=None):
                seen["extra"] = get_flow_log_extra()
                raise RuntimeError("boom")

        svc = BoomService()
        svc._runtime_attrs = {"root_pipeline_id": "r1", "id": "n1", "version": "v1"}
        self.assertFalse(svc.schedule(self._data(), None))
        self.assertIsNotNone(seen.get("extra"))
        self.assertIsNone(get_flow_log_extra())
