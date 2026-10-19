# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import hashlib
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator import DbConsoleDumpFlowValidator


def _make_validator(data: dict) -> DbConsoleDumpFlowValidator:
    """绕过 BaseValidator.__new__ 的立刻 __call__，便于单测私有方法。"""
    validator = object.__new__(DbConsoleDumpFlowValidator)
    validator.data = data
    return validator


class TestDbConsoleDumpFlowValidatorInject(SimpleTestCase):
    """覆盖 where 注入检查：命中拒绝 / 放行进 EXPLAIN / API 异常失败放行。"""

    def test_empty_where_skips_all_checks(self):
        with patch.object(DbConsoleDumpFlowValidator, "_check_where_inject") as mock_inject, patch.object(
            DbConsoleDumpFlowValidator, "_explain_all"
        ) as mock_explain:
            result = DbConsoleDumpFlowValidator({"where": "", "cluster_id": 1, "databases": ["db1"], "tables": ["t1"]})
            self.assertIsNone(result)
            mock_inject.assert_not_called()
            mock_explain.assert_not_called()

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.SQLSimulationApi.syntax_check_inject"
    )
    def test_union_where_rejected_by_inject(self, mock_inject):
        mock_inject.return_value = {"is_inject": True, "reason": "检测到 UNION 查询拼接"}
        validator = _make_validator({})
        err = validator._check_where_inject("111 union select * from t2", ("db1", "t1"))
        self.assertIsNotNone(err)
        self.assertEqual(err["field"], "where")
        self.assertIn("UNION", err["errors"])
        mock_inject.assert_called_once_with(
            params={
                "sql": "SELECT * FROM `db1`.`t1` WHERE (111 union select * from t2)",
                "judge_subquery_diff_table": True,
            },
            timeout=DbConsoleDumpFlowValidator.INJECT_CHECK_TIMEOUT,
            retry_times=DbConsoleDumpFlowValidator.INJECT_CHECK_RETRY_TIMES,
        )

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.SQLSimulationApi.syntax_check_inject",
        return_value={"is_inject": False, "reason": ""},
    )
    @patch.object(DbConsoleDumpFlowValidator, "_explain_all", return_value=[])
    @patch.object(DbConsoleDumpFlowValidator, "_resolve_targets", return_value=([("db1", "t1")], []))
    @patch.object(DbConsoleDumpFlowValidator, "_get_read_address", return_value=("127.0.0.1:20000", 0))
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.Cluster.objects.get",
        return_value=MagicMock(),
    )
    def test_clean_where_passes_inject_then_explain(
        self, mock_cluster, mock_addr, mock_resolve, mock_explain, mock_inject
    ):
        result = DbConsoleDumpFlowValidator(
            {
                "where": "id > 1",
                "cluster_id": 1,
                "databases": ["db1"],
                "tables": ["t1"],
            }
        )
        self.assertIsNone(result)
        mock_inject.assert_called_once()
        mock_explain.assert_called_once()
        self.assertEqual(mock_explain.call_args[0][2], "id > 1")
        self.assertEqual(mock_explain.call_args[0][3], [("db1", "t1")])

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.SQLSimulationApi.syntax_check_inject",
        side_effect=RuntimeError("simulation down"),
    )
    @patch.object(DbConsoleDumpFlowValidator, "_explain_all", return_value=[])
    @patch.object(DbConsoleDumpFlowValidator, "_resolve_targets", return_value=([("db1", "t1")], []))
    @patch.object(DbConsoleDumpFlowValidator, "_get_read_address", return_value=("127.0.0.1:20000", 0))
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.Cluster.objects.get",
        return_value=MagicMock(),
    )
    def test_inject_api_error_fail_open(self, mock_cluster, mock_addr, mock_resolve, mock_explain, mock_inject):
        result = DbConsoleDumpFlowValidator(
            {
                "where": "id > 1",
                "cluster_id": 1,
                "databases": ["db1"],
                "tables": ["t1"],
            }
        )
        self.assertIsNone(result)
        mock_inject.assert_called_once()
        mock_explain.assert_called_once()


def _query(
    query_id,
    command="select",
    refs=None,
    digest="SELECT ? ",
    inject=False,
    reason="",
    error_code=0,
    error_msg="",
    db_name="",
):
    return {
        "query_id": query_id,
        "command": command,
        "db_name": db_name,
        "error_code": error_code,
        "error_msg": error_msg,
        "table_references": [] if refs is None else refs,
        "query_digest_text": digest,
        "is_inject": inject,
        "reason": reason,
    }


def _ref(db_name, table_name):
    return {"db_name": db_name, "table_name": table_name}


class TestDbConsoleDumpSqlExport(SimpleTestCase):
    def _run(self, lines, raw=b"SELECT 1;\n", rpc_side_effect=None):
        data = {
            "export_mode": "sql",
            "cluster_id": 1,
            "sql_path": "mysql/sqlfile/1",
            "sql_filename": "a.sql",
        }
        digest = hashlib.sha256(raw).hexdigest()
        started = [
            patch.object(DbConsoleDumpFlowValidator, "_load_sql_bytes", return_value=(raw, None)),
            patch.object(
                DbConsoleDumpFlowValidator,
                "_fetch_parsed_queries",
                return_value={"content_sha256": digest, "queries": lines},
            ),
        ]
        if rpc_side_effect is not None:
            started.extend(
                [
                    patch(
                        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.Cluster.objects.get",
                        return_value=MagicMock(),
                    ),
                    patch.object(DbConsoleDumpFlowValidator, "_get_read_address", return_value=("127.0.0.1:20000", 0)),
                    patch(
                        "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.DRSApi.rpc",
                        side_effect=rpc_side_effect,
                    ),
                ]
            )
        for item in started:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in started])
        return DbConsoleDumpFlowValidator(data), data

    @staticmethod
    def _rpc(rows):
        return [{"error_msg": "", "cmd_results": [{"error_msg": "", "table_data": rows}]}]

    def test_accept_use_and_select_writes_sha(self):
        lines = [
            _query(1, command="change_db", db_name="app", digest="USE `app` "),
            _query(2, refs=[_ref("app", "t")], digest="SELECT `id` FROM `t` "),
        ]
        rpc = [
            self._rpc([{"v": "0"}]),
            self._rpc([{"TABLE_SCHEMA": "app", "TABLE_NAME": "t"}]),
        ]
        raw = b"USE app;\nSELECT id FROM t;\n"
        result, data = self._run(lines, raw=raw, rpc_side_effect=rpc)
        self.assertIsNone(result)
        self.assertEqual(data["sql_sha256"], hashlib.sha256(raw).hexdigest())

    def test_insert_carries_query_id(self):
        lines = [
            _query(1, command="change_db", db_name="app", digest="USE `app` "),
            _query(2, command="insert", digest="INSERT INTO `app` . `t` "),
        ]
        result, unused_data = self._run(lines)
        text = " ".join(item["errors"] for item in result)
        self.assertIn("2", text)

    def test_system_db_and_derived(self):
        lines = [
            _query(1, refs=[_ref("information_schema", "TABLES")]),
            _query(2, refs=[_ref("INFORMATION_SCHEMA", "TABLES")]),
            _query(3, refs=[], digest="SELECT * FROM ( SELECT * FROM `mysql` . `user` ) AS `dt` "),
        ]
        result, unused_data = self._run(lines)
        text = " ".join(item["errors"] for item in result)
        self.assertIn("1", text)
        self.assertIn("2", text)
        self.assertIn("3", text)

    def test_missing_use(self):
        lines = [_query(4, refs=[_ref("", "t")], digest="SELECT `id` FROM `t` ")]
        result, unused_data = self._run(lines)
        text = " ".join(item["errors"] for item in result)
        self.assertIn("4", text)
        self.assertIn("缺少库名", text)

    def test_missing_table(self):
        lines = [_query(5, refs=[_ref("db", "t")], digest="SELECT `id` FROM `db` . `t` ")]
        rpc = [self._rpc([{"v": "0"}]), self._rpc([])]
        result, unused_data = self._run(lines, rpc_side_effect=rpc)
        text = " ".join(item["errors"] for item in result)
        self.assertIn("db.t", text)
        self.assertIn("5", text)

    def test_many_selects_and_quoted_semicolon(self):
        lines = [_query(index) for index in range(1, 21)]
        result, unused_data = self._run(lines)
        self.assertIsNone(result)
        one, unused_again = self._run([_query(1)])
        self.assertIsNone(one)

    def test_comment_only(self):
        lines = [_query(1, command="unknown", error_code=1065, error_msg="Query was empty")]
        result, unused_data = self._run(lines)
        self.assertTrue(result)

    def test_set_option_with_select_is_allowed(self):
        lines = [
            _query(1, command="set_option", digest="SET NAMES ? "),
            _query(2, command="set_option", digest="SET @row_limit = ? "),
            _query(3, command="set_option", digest="SET SESSION transaction_isolation = ? "),
            _query(4),
        ]
        result, unused_data = self._run(lines)
        self.assertIsNone(result)

    def test_sleep_and_insert_together(self):
        lines = [
            _query(1, inject=True, reason="检测到 SLEEP/BENCHMARK 时间盲注函数"),
            _query(2),
            _query(3, command="insert"),
        ]
        result, unused_data = self._run(lines)
        text = " ".join(item["errors"] for item in result)
        self.assertIn("1", text)
        self.assertIn("3", text)
        self.assertIn("SLEEP", text)

    def test_derived_join_rejects_system_db_in_digest(self):
        lines = [
            _query(
                6,
                refs=[_ref("app", "u")],
                digest="SELECT * FROM ( SELECT `id` FROM `mysql` . `user` ) `dt` JOIN `app` . `u` ",
            ),
            _query(
                7,
                refs=[_ref("app", "u")],
                digest="SELECT ( SELECT MAX(`id`) FROM `mysql` . `user` ) FROM `app` . `u` ",
            ),
        ]
        result, unused_data = self._run(lines)
        text = " ".join(item["errors"] for item in result)
        self.assertIn("6", text)
        self.assertIn("7", text)

    def test_business_join_is_not_a_system_db(self):
        lines = [
            _query(
                1,
                refs=[_ref("app", "t"), _ref("app", "u")],
                digest="SELECT * FROM `app` . `t` JOIN `app` . `u` ",
            )
        ]
        rpc = [
            self._rpc([{"v": "0"}]),
            self._rpc(
                [
                    {"TABLE_SCHEMA": "app", "TABLE_NAME": "t"},
                    {"TABLE_SCHEMA": "app", "TABLE_NAME": "u"},
                ]
            ),
        ]
        result, unused_data = self._run(lines, rpc_side_effect=rpc)
        self.assertIsNone(result)

    def test_hash_mismatch_does_not_store(self):
        data = {
            "export_mode": "sql",
            "cluster_id": 1,
            "sql_path": "mysql/sqlfile/1",
            "sql_filename": "a.sql",
        }
        raw = b"SELECT 1;\n"
        validator = _make_validator(data)
        with patch.object(DbConsoleDumpFlowValidator, "_load_sql_bytes", return_value=(raw, None)), patch.object(
            DbConsoleDumpFlowValidator,
            "_fetch_parsed_queries",
            return_value={"content_sha256": "0" * 64, "queries": [_query(1)]},
        ):
            result = validator._validate_sql_export()
        self.assertTrue(result)
        self.assertNotIn("sql_sha256", data)

    def test_bad_download_does_not_store_hash(self):
        validator = _make_validator({"sql_path": "mysql/sqlfile/1", "sql_filename": "a.sql"})
        resp = MagicMock()
        resp.status_code = 404
        resp.content = b'{"message":"missing"}'
        storage = MagicMock()
        storage.client.batch_download.return_value = resp
        with patch(
            "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.get_storage",
            return_value=storage,
        ):
            raw, err = validator._load_sql_bytes()
        self.assertIsNone(raw)
        self.assertIsNotNone(err)
        self.assertNotIn("sql_sha256", validator.data)
        resp.status_code = 200
        resp.content = b""
        with patch(
            "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.get_storage",
            return_value=storage,
        ):
            raw, err = validator._load_sql_bytes()
        self.assertIsNone(raw)
        self.assertNotIn("sql_sha256", validator.data)
        resp.content = b"\xff"
        with patch(
            "backend.flow.engine.bamboo.scene.mysql.validate.dbconsole_dump_validator.get_storage",
            return_value=storage,
        ):
            raw, err = validator._load_sql_bytes()
        self.assertIsNone(raw)
        self.assertNotIn("sql_sha256", validator.data)
