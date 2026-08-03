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
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.flow.utils import sql_exec_duration_recorder as recorder
from backend.flow.utils.job_log_parser import SqlExecRecord


class TestSqlExecDurationEnrich(SimpleTestCase):
    """覆盖 SQL 解析回填与 size 分支（不连真实 DB）。"""

    def test_extract_sql_meta_update(self):
        queries = [
            {"query_id": 1, "command": "change_db", "db_name": "db1", "table_name": "", "error_line": 0},
            {"query_id": 2, "command": "update", "db_name": "db1", "table_name": "t1", "error_line": 0},
        ]
        meta = recorder._extract_sql_meta(queries, fallback_db="fallback")
        self.assertEqual(meta["sql_type"], "update")
        self.assertEqual(meta["table_name"], "t1")
        self.assertEqual(meta["size_db"], "db1")

    def test_extract_sql_meta_multi_tables(self):
        queries = [
            {"command": "delete", "db_name": "db1", "table_name": "t1"},
            {"command": "delete", "db_name": "db1", "table_name": "t2"},
        ]
        meta = recorder._extract_sql_meta(queries, fallback_db="")
        self.assertEqual(meta["sql_type"], "delete")
        self.assertEqual(meta["table_name"], "t1,t2")
        self.assertEqual(meta["table_names"], ["t1", "t2"])

    def test_resolve_table_size_skip_call(self):
        size = recorder._resolve_table_size(
            sql_type="call",
            cluster_domain="gamedb.example.db",
            size_db="db1",
            table_names=["proc"],
        )
        self.assertIsNone(size)

    @patch.object(recorder, "_query_database_size_bytes", return_value=1000)
    def test_resolve_table_size_drop_db(self, mock_db_size):
        size = recorder._resolve_table_size(
            sql_type="drop_db",
            cluster_domain="gamedb.example.db",
            size_db="db1",
            table_names=[],
        )
        self.assertEqual(size, 1000)
        mock_db_size.assert_called_once()

    @patch.object(recorder, "_query_table_size_bytes", return_value=200)
    def test_resolve_table_size_normal(self, mock_tbl_size):
        size = recorder._resolve_table_size(
            sql_type="update",
            cluster_domain="gamedb.example.db",
            size_db="db1",
            table_names=["t1"],
        )
        self.assertEqual(size, 200)
        mock_tbl_size.assert_called_once()

    @patch.object(recorder.MysqlSqlExecDuration.objects, "bulk_create")
    @patch.object(recorder.MysqlSqlExecDuration.objects, "filter")
    @patch.object(recorder, "_resolve_sim_cluster_type", return_value="mysql")
    @patch.object(recorder, "_parse_sql_queries")
    def test_persist_fills_fields_and_parse_fail_ok(self, mock_parse, mock_ctype, mock_filter, mock_bulk):
        mock_filter.return_value.values_list.return_value = []
        mock_parse.return_value = [
            {"command": "update", "db_name": "db1", "table_name": "t1"},
        ]
        with patch.object(recorder, "_resolve_table_size", return_value=42) as mock_size:
            records = [
                SqlExecRecord(
                    job_instance_id=1,
                    step_instance_id=2,
                    ip="127.0.0.1",
                    bk_cloud_id=0,
                    db="db1",
                    sql="UPDATE t1 SET a=1",
                    duration_sec=60.0,
                )
            ]
            n = recorder._persist(
                sql_records=records,
                root_id="root1",
                cluster_id=1,
                cluster_domain="gamedb.example.db",
                ticket_id=9,
            )
            self.assertEqual(n, 1)
            mock_bulk.assert_called_once()
            obj = mock_bulk.call_args[0][0][0]
            self.assertEqual(obj.sql_type, "update")
            self.assertEqual(obj.table_name, "t1")
            self.assertEqual(obj.table_size, 42)
            mock_size.assert_called_once()

        # 解析失败：仍能入库，字段留空
        mock_bulk.reset_mock()
        mock_parse.return_value = []
        records[0] = SqlExecRecord(
            job_instance_id=1,
            step_instance_id=2,
            ip="127.0.0.1",
            bk_cloud_id=0,
            db="db1",
            sql="SELECT 1",
            duration_sec=90.0,
        )
        # 换 checksum：改 sql
        n = recorder._persist(
            sql_records=records,
            root_id="root1",
            cluster_id=1,
            cluster_domain="gamedb.example.db",
            ticket_id=9,
        )
        self.assertEqual(n, 1)
        obj = mock_bulk.call_args[0][0][0]
        self.assertEqual(obj.sql_type, "")
        self.assertEqual(obj.table_name, "")
        self.assertIsNone(obj.table_size)

    @patch.object(recorder, "_sum_table_sizes_for_role")
    def test_query_table_size_shard_sum_path(self, mock_sum):
        # 第一次 slave 无数据，第二次 orphan 有值
        mock_sum.side_effect = [None, 300]
        size = recorder._query_table_size_bytes(
            cluster_domain="spider.example.db",
            db_name="db1",
            table_names=["t1"],
        )
        self.assertEqual(size, 300)
        self.assertEqual(mock_sum.call_count, 2)
