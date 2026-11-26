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
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType
from backend.db_services.mysql.dts.schema_sql import build_hetero_schema_sql, to_tspider_create
from backend.db_services.mysql.remote_service.exceptions import RemoteServiceBaseException
from backend.ticket.builders.mysql.dts.mysql_dts_tickets import parse_target_schema_sql

_SINGLE_PK = """CREATE TABLE `t1` (
  `id` int NOT NULL,
  `name` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""

_COMPOSITE_PK = """CREATE TABLE `t2` (
  `id` int NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`, `user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='biz'"""


class TspiderCreateTest(SimpleTestCase):
    def test_single_primary_key_becomes_spider_comment(self):
        sql, shard_key = to_tspider_create(_SINGLE_PK)
        self.assertEqual(shard_key, "id")
        self.assertIn("ENGINE=SPIDER", sql)
        self.assertNotIn("ENGINE=InnoDB", sql)
        self.assertIn("COMMENT='shard_key \"id\"'", sql)
        self.assertTrue(sql.endswith(";"))

    def test_composite_primary_key_keeps_comment_and_omits_shard_key(self):
        sql, shard_key = to_tspider_create(_COMPOSITE_PK)
        self.assertEqual(shard_key, "")
        self.assertIn("ENGINE=SPIDER", sql)
        self.assertIn("COMMENT='biz'", sql)
        self.assertNotIn("shard_key", sql)


class BuildHeteroSchemaSqlTest(SimpleTestCase):
    def setUp(self):
        self.payload = {
            "cluster_id": 1000293,
            "target_cluster_id": 1000294,
            "db_patterns": ["test_db"],
            "ignore_dbs": [],
            "table_patterns": ["*"],
            "ignore_tables": ["skip_*"],
        }

    def _cluster(self, cluster_id, cluster_type):
        return SimpleNamespace(id=cluster_id, bk_biz_id=3, cluster_type=cluster_type, bk_cloud_id=0)

    def _rpc(self, payload):
        cmds = payload["cmds"]
        if cmds[0].lstrip().upper().startswith("SELECT"):
            include = [
                {"TABLE_SCHEMA": "test_db", "TABLE_NAME": "t1"},
                {"TABLE_SCHEMA": "test_db", "TABLE_NAME": "t2"},
                {"TABLE_SCHEMA": "test_db", "TABLE_NAME": "skip_me"},
            ]
            ignored = [{"TABLE_SCHEMA": "test_db", "TABLE_NAME": "skip_me"}]
            table_data = [include, ignored]
        else:
            creates = {
                "`t1`": _SINGLE_PK,
                "`t2`": _COMPOSITE_PK,
            }
            table_data = [
                [{"Create Table": next(sql for name, sql in creates.items() if name in cmd)}] for cmd in cmds
            ]
        return [
            {
                "error_msg": "",
                "cmd_results": [
                    {"cmd": cmd, "table_data": rows, "error_msg": ""} for cmd, rows in zip(cmds, table_data)
                ],
            }
        ]

    @patch(
        "backend.db_services.mysql.dts.schema_sql.RemoteServiceHandler.show_database_with_pattern",
        return_value=["test_db"],
    )
    @patch("backend.db_services.mysql.dts.schema_sql.RemoteServiceHandler._get_cluster_address")
    @patch("backend.db_services.mysql.dts.schema_sql.DRSApi.rpc")
    @patch("backend.db_services.mysql.dts.schema_sql.Cluster.objects.get")
    def test_returns_whole_sql_and_ticket_parser_can_read_it(self, get_cluster, rpc, get_address, _show_db):
        get_cluster.side_effect = [
            self._cluster(1000293, ClusterType.TenDBHA.value),
            self._cluster(1000294, ClusterType.TenDBCluster.value),
        ]
        get_address.return_value = (SimpleNamespace(cluster=SimpleNamespace(bk_cloud_id=0)), "127.0.0.1:3306")
        rpc.side_effect = self._rpc

        result = build_hetero_schema_sql(3, self.payload)

        self.assertTrue(result["sql"].startswith("-- source_cluster_id: 1000293\n"))
        self.assertIn("USE `test_db`;", result["sql"])
        self.assertNotIn("skip_me", result["sql"])
        self.assertEqual(
            parse_target_schema_sql(result["sql"]),
            [("test_db", "t1", "id"), ("test_db", "t2", "")],
        )
        self.assertEqual(result["tables"][0]["shard_key"], "id")
        self.assertEqual(result["tables"][1]["shard_key"], "")
        header = result["sql"].split("CREATE TABLE", 1)[0]
        self.assertNotIn("\nCREATE TABLE", "\n" + header)

    @patch(
        "backend.db_services.mysql.dts.schema_sql.RemoteServiceHandler.show_database_with_pattern",
        return_value=["test_db"],
    )
    @patch("backend.db_services.mysql.dts.schema_sql.RemoteServiceHandler._get_cluster_address")
    @patch("backend.db_services.mysql.dts.schema_sql.DRSApi.rpc")
    @patch("backend.db_services.mysql.dts.schema_sql.Cluster.objects.get")
    def test_any_show_create_failure_rejects_the_whole_request(self, get_cluster, rpc, get_address, _show_db):
        get_cluster.side_effect = [
            self._cluster(1000293, ClusterType.TenDBHA.value),
            self._cluster(1000294, ClusterType.TenDBCluster.value),
        ]
        get_address.return_value = (SimpleNamespace(cluster=SimpleNamespace(bk_cloud_id=0)), "127.0.0.1:3306")

        def broken(payload):
            response = self._rpc(payload)
            if payload["cmds"][0].startswith("SHOW CREATE"):
                response[0]["cmd_results"][1]["table_data"] = []
            return response

        rpc.side_effect = broken
        with self.assertRaises(RemoteServiceBaseException):
            build_hetero_schema_sql(3, self.payload)

    @patch("backend.db_services.mysql.dts.schema_sql.Cluster.objects.get")
    def test_rejects_tendbcluster_source(self, get_cluster):
        get_cluster.return_value = self._cluster(1000293, ClusterType.TenDBCluster.value)
        with self.assertRaises(RemoteServiceBaseException):
            build_hetero_schema_sql(3, self.payload)
