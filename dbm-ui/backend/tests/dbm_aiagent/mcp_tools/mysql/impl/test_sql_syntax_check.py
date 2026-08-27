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
from datetime import datetime
from datetime import timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check import (
    LARGE_TABLE_MIN_BYTES,
    _format_capacity,
    _format_duration,
    parse_sql_file_statement_impl,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.sql_syntax_check import ParseSqlFileStatementInputSerializer

_MIB = 1024**2
_GIB = 1024**3


def _parse_result():
    return {
        "command_counts": {"alter_table": 2, "drop_table": 1, "truncate": 1, "change_db": 1},
        "file_command_counts": {"a.sql": {"alter_table": 2, "change_db": 1}},
        "alter_tables": [
            {
                "file_name": "a.sql",
                "alters": [
                    {"db_name": "db1", "table_name": "t1"},
                    {"db_name": "", "table_name": "t_empty"},
                ],
            }
        ],
        "drop_tables": [{"file_name": "a.sql", "tables": [{"db_name": "db1", "table_name": "t2"}]}],
        "truncate_tables": [{"file_name": "b.sql", "tables": [{"db_name": "", "table_name": "t3"}]}],
    }


class _SizeQuery:
    def __init__(self, rows_by_role):
        self.rows_by_role = rows_by_role
        self.role = None

    def filter(self, **kwargs):
        if "instance_role" in kwargs:
            self.role = kwargs["instance_role"]
        return self

    def values(self, *args):
        return self

    def annotate(self, **kwargs):
        return self

    def order_by(self, *args):
        return list(self.rows_by_role.get(self.role, []))


class _DurationQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, **kwargs):
        return self

    def order_by(self, *args):
        return self.rows


def _cluster(cluster_id=21009276, domain="spider.bj1-event.dnf.db", bk_biz_id=1001):
    cluster = MagicMock()
    cluster.id = cluster_id
    cluster.pk = cluster_id
    cluster.immute_domain = domain
    cluster.bk_biz_id = bk_biz_id
    return cluster


class TestParseSqlFileStatementInputSerializer(SimpleTestCase):
    def test_include_sql_text_defaults_false_when_omitted(self):
        slz = ParseSqlFileStatementInputSerializer(data={"path": "mysql/sqlfile/123", "file_list": ["a.sql"]})
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertIs(slz.validated_data["include_sql_text"], False)
        self.assertEqual(slz.validated_data["cluster_ids"], [])
        self.assertEqual(slz.validated_data["execute_objects"], [])

    def test_include_sql_text_true_when_passed(self):
        slz = ParseSqlFileStatementInputSerializer(
            data={"path": "mysql/sqlfile/123", "file_list": ["a.sql"], "include_sql_text": True}
        )
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertIs(slz.validated_data["include_sql_text"], True)

    def test_cluster_ids_and_execute_objects(self):
        slz = ParseSqlFileStatementInputSerializer(
            data={
                "path": "mysql/sqlfile/123",
                "file_list": ["a.sql"],
                "cluster_ids": [21009276],
                "execute_objects": [
                    {
                        "dbnames": ["db_%"],
                        "ignore_dbnames": ["db_tmp"],
                        "sql_files": ["a.sql"],
                        "line_id": 1,
                    }
                ],
            }
        )
        self.assertTrue(slz.is_valid(), slz.errors)
        self.assertEqual(slz.validated_data["cluster_ids"], [21009276])
        self.assertEqual(slz.validated_data["execute_objects"][0]["dbnames"], ["db_%"])
        self.assertEqual(slz.validated_data["execute_objects"][0]["ignore_dbnames"], ["db_tmp"])


class TestCapacityFormat(SimpleTestCase):
    def test_m_and_g_strip_integer_decimal(self):
        self.assertEqual(_format_capacity(800 * _MIB), "800M")
        self.assertEqual(_format_capacity(227 * _GIB), "227G")
        self.assertEqual(_format_capacity(int(3.4 * _GIB)), "3.4G")
        self.assertEqual(_format_capacity(_GIB), "1G")

    def test_duration_format(self):
        self.assertEqual(_format_duration(32), "32s")
        self.assertEqual(_format_duration(32.0), "32s")
        self.assertEqual(_format_duration(1.5), "1.5s")


class TestParseSqlFileStatementImpl(SimpleTestCase):
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check.SQLSimulationApi.parse_file_statement")
    def test_maps_file_list_to_files_and_sends_include_sql_text_false(self, mock_api):
        mock_api.return_value = _parse_result()
        result = parse_sql_file_statement_impl(path="mysql/sqlfile/123", file_list=["a.sql", "b.sql"])
        mock_api.assert_called_once()
        params = mock_api.call_args.kwargs["params"]
        self.assertEqual(params["path"], "mysql/sqlfile/123")
        self.assertEqual(params["files"], ["a.sql", "b.sql"])
        self.assertIs(params["include_sql_text"], False)
        self.assertEqual(mock_api.call_args.kwargs["headers"], {"platform": "mcp"})
        self.assertEqual(result["large_tables"], [])
        self.assertNotIn("alter_tables", result)
        self.assertNotIn("drop_tables", result)
        self.assertNotIn("truncate_tables", result)
        self.assertEqual(result["command_counts"]["alter_table"], 2)

    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check.SQLSimulationApi.parse_file_statement")
    def test_forwards_include_sql_text_true(self, mock_api):
        mock_api.return_value = {}
        parse_sql_file_statement_impl(path="mysql/sqlfile/123", file_list=["a.sql"], include_sql_text=True)
        self.assertIs(mock_api.call_args.kwargs["params"]["include_sql_text"], True)

    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check.SQLSimulationApi.parse_file_statement")
    def test_raises_on_api_failure(self, mock_api):
        mock_api.side_effect = Exception("parse failed")
        with self.assertRaisesMessage(Exception, "parse failed"):
            parse_sql_file_statement_impl(path="mysql/sqlfile/123", file_list=["a.sql"])


class TestParseSqlFileStatementLargeTables(SimpleTestCase):
    def _run(
        self, parse_result=None, sizes=None, durations=None, expanded_dbs=None, cluster_ids=None, execute_objects=None
    ):
        cluster = _cluster()
        cluster_qs = MagicMock()
        cluster_qs.filter.return_value = [cluster]
        size_rows = sizes if sizes is not None else []
        duration_rows = durations if durations is not None else []
        handler = MagicMock()
        handler.show_database_with_pattern.return_value = expanded_dbs if expanded_dbs is not None else ["db_a"]

        with patch(
            "backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check.SQLSimulationApi.parse_file_statement"
        ) as mock_api, patch(
            "backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check.Cluster"
        ) as mock_cluster, patch(
            "backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check.MysqlDbTableSize"
        ) as mock_size, patch(
            "backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check.MysqlSqlExecDuration"
        ) as mock_duration, patch(
            "backend.dbm_aiagent.mcp_tools.mysql.impl.sql_syntax_check.RemoteServiceHandler",
            return_value=handler,
        ):
            mock_api.return_value = parse_result if parse_result is not None else _parse_result()
            mock_cluster.objects.using.return_value = cluster_qs
            mock_size.objects = _SizeQuery({"slave": size_rows})
            mock_duration.objects = _DurationQuery(duration_rows)
            result = parse_sql_file_statement_impl(
                path="mysql/sqlfile/123",
                file_list=["a.sql"],
                cluster_ids=cluster_ids if cluster_ids is not None else [21009276],
                execute_objects=execute_objects if execute_objects is not None else [],
            )
        return result, handler

    def test_named_db_used_directly_without_execute_objects(self):
        sizes = [
            {
                "cluster_domain": "spider.bj1-event.dnf.db",
                "database_name": "db1",
                "table_name": "t1",
                "dteventtimehour": datetime(2026, 8, 27, 10, tzinfo=dt_timezone.utc),
                "table_size": 227 * _GIB,
            },
            {
                "cluster_domain": "spider.bj1-event.dnf.db",
                "database_name": "db1",
                "table_name": "t2",
                "dteventtimehour": datetime(2026, 8, 27, 10, tzinfo=dt_timezone.utc),
                "table_size": 800 * _MIB,
            },
        ]
        result, handler = self._run(sizes=sizes)
        handler.show_database_with_pattern.assert_not_called()
        cluster_payload = result["large_tables"][0]
        self.assertEqual(cluster_payload["cluster_id"], 21009276)
        self.assertEqual(cluster_payload["cluster_domain"], "spider.bj1-event.dnf.db")
        self.assertEqual(cluster_payload["databases"]["db1"]["alter_tables"][0]["name"], "t1")
        self.assertEqual(cluster_payload["databases"]["db1"]["alter_tables"][0]["size"], "227G")
        self.assertNotIn("last_change_info", cluster_payload["databases"]["db1"]["alter_tables"][0])
        self.assertEqual(cluster_payload["databases"]["db1"]["drop_tables"][0]["size"], "800M")
        self.assertNotIn("truncate_tables", cluster_payload["databases"]["db1"])
        self.assertNotIn("alter_tables", result)

    def test_empty_db_name_skipped_without_execute_objects(self):
        sizes = [
            {
                "cluster_domain": "spider.bj1-event.dnf.db",
                "database_name": "db_a",
                "table_name": "t_empty",
                "dteventtimehour": datetime(2026, 8, 27, 10, tzinfo=dt_timezone.utc),
                "table_size": _GIB,
            }
        ]
        result, handler = self._run(sizes=sizes, expanded_dbs=["db_a"])
        handler.show_database_with_pattern.assert_not_called()
        self.assertEqual(result["large_tables"], [])

    def test_empty_db_name_expanded_by_execute_objects(self):
        sizes = [
            {
                "cluster_domain": "spider.bj1-event.dnf.db",
                "database_name": "db_a",
                "table_name": "t_empty",
                "dteventtimehour": datetime(2026, 8, 27, 10, tzinfo=dt_timezone.utc),
                "table_size": _GIB,
            }
        ]
        result, handler = self._run(
            sizes=sizes,
            expanded_dbs=["db_a"],
            execute_objects=[{"dbnames": ["db_%"], "ignore_dbnames": [], "sql_files": ["a.sql"]}],
        )
        handler.show_database_with_pattern.assert_called()
        self.assertEqual(result["large_tables"][0]["databases"]["db_a"]["alter_tables"][0]["name"], "t_empty")

    def test_below_threshold_excluded(self):
        sizes = [
            {
                "cluster_domain": "spider.bj1-event.dnf.db",
                "database_name": "db1",
                "table_name": "t1",
                "dteventtimehour": datetime(2026, 8, 27, 10, tzinfo=dt_timezone.utc),
                "table_size": LARGE_TABLE_MIN_BYTES - 1,
            }
        ]
        result, unused_handler = self._run(sizes=sizes)
        self.assertEqual(result["large_tables"], [])

    def test_last_change_info_optional_fields(self):
        sizes = [
            {
                "cluster_domain": "spider.bj1-event.dnf.db",
                "database_name": "db1",
                "table_name": "t1",
                "dteventtimehour": datetime(2026, 8, 27, 10, tzinfo=dt_timezone.utc),
                "table_size": 227 * _GIB,
            }
        ]
        rec = SimpleNamespace(
            cluster_id=21009276,
            db_name="db1",
            table_name="t1",
            sql_type="alter_table",
            created_at=datetime(2026, 8, 1, tzinfo=dt_timezone.utc),
            ticket_id=2449023,
            table_size=227 * _GIB,
            duration_sec=32,
        )
        result, unused_handler = self._run(sizes=sizes, durations=[rec])
        info = result["large_tables"][0]["databases"]["db1"]["alter_tables"][0]["last_change_info"]
        self.assertEqual(info["ticket_id"], 2449023)
        self.assertEqual(info["table_size"], "227G")
        self.assertEqual(info["duration"], "32s")
