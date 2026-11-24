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
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.utils.mysql.cluster_variables.collector import (
    ClusterVariableQueryError,
    _collect_query_addresses,
    build_show_variables_sql,
    query_variables_for_addresses,
)
from backend.flow.utils.mysql.cluster_variables.diff import (
    build_spider_version,
    build_tendbcluster_variable_diff,
    build_tendbha_variable_diff,
    diff_variables,
)


def _drs_item(address, variables=None, error_msg="", cmd_error_msg=""):
    return {
        "address": address,
        "error_msg": error_msg,
        "cmd_results": [
            {
                "error_msg": cmd_error_msg,
                "table_data": [{"Variable_name": k, "Value": v} for k, v in (variables or {}).items()],
            }
        ],
    }


class TestBuildShowVariablesSql(unittest.TestCase):
    def test_empty_returns_full_show(self):
        self.assertEqual(build_show_variables_sql(), "SHOW GLOBAL VARIABLES")
        self.assertEqual(build_show_variables_sql([]), "SHOW GLOBAL VARIABLES")

    def test_whitelist_dedup_and_order(self):
        sql = build_show_variables_sql(["sql_mode", "wait_timeout", "sql_mode"])
        self.assertEqual(sql, "SHOW GLOBAL VARIABLES WHERE Variable_name IN ('sql_mode','wait_timeout')")

    def test_rejects_unsafe_name(self):
        with self.assertRaises(ClusterVariableQueryError):
            build_show_variables_sql(["sql_mode; DROP TABLE x"])


class TestQueryVariablesForAddresses(unittest.TestCase):
    def test_whitelist_and_out_of_order_mapping(self):
        captured = {}

        def fake_rpc(payload):
            captured["payload"] = payload
            return [
                _drs_item("127.0.0.2:20000", {"sql_mode": "STRICT"}),
                _drs_item("127.0.0.1:20000", {"sql_mode": "TRADITIONAL"}),
            ]

        addr_vars, unused_meta, errors = query_variables_for_addresses(
            bk_cloud_id=0,
            addresses=["127.0.0.1:20000", "127.0.0.2:20000"],
            variable_names=["sql_mode"],
            fail_fast=False,
            rpc_func=fake_rpc,
        )
        self.assertEqual(captured["payload"]["cmds"], ["SHOW GLOBAL VARIABLES WHERE Variable_name IN ('sql_mode')"])
        self.assertEqual(addr_vars["127.0.0.1:20000"]["sql_mode"], "TRADITIONAL")
        self.assertEqual(addr_vars["127.0.0.2:20000"]["sql_mode"], "STRICT")
        self.assertEqual(errors, {})

    def test_fail_fast_false_collects_errors_without_aborting(self):
        def fake_rpc(payload):
            return [
                _drs_item("127.0.0.1:20000", {"sql_mode": "STRICT"}),
                _drs_item("127.0.0.2:20000", error_msg="connect timeout"),
            ]

        addr_vars, unused_meta, errors = query_variables_for_addresses(
            bk_cloud_id=0,
            addresses=["127.0.0.1:20000", "127.0.0.2:20000", "127.0.0.3:20000"],
            fail_fast=False,
            rpc_func=fake_rpc,
        )
        self.assertIn("127.0.0.1:20000", addr_vars)
        self.assertNotIn("127.0.0.2:20000", addr_vars)
        self.assertEqual(errors["127.0.0.2:20000"], "connect timeout")
        self.assertIn("127.0.0.3:20000", errors)

    def test_fail_fast_true_raises_on_error(self):
        def fake_rpc(payload):
            return [_drs_item("127.0.0.1:20000", error_msg="denied")]

        with self.assertRaises(ClusterVariableQueryError):
            query_variables_for_addresses(
                bk_cloud_id=0,
                addresses=["127.0.0.1:20000"],
                fail_fast=True,
                rpc_func=fake_rpc,
            )

    def test_collect_query_addresses_only_standby_slaves_for_tendbha(self):
        storage_set = MagicMock()
        storage_set.all.return_value = [
            SimpleNamespace(
                ip_port="127.0.0.1:20000", instance_role=InstanceRole.BACKEND_MASTER.value, is_stand_by=False
            ),
            SimpleNamespace(
                ip_port="127.0.0.2:20000", instance_role=InstanceRole.BACKEND_SLAVE.value, is_stand_by=True
            ),
            SimpleNamespace(
                ip_port="127.0.0.3:20000", instance_role=InstanceRole.BACKEND_SLAVE.value, is_stand_by=False
            ),
        ]
        cluster = SimpleNamespace(cluster_type=ClusterType.TenDBHA.value, storageinstance_set=storage_set)
        self.assertEqual(
            _collect_query_addresses(cluster, only_standby_slaves=False),
            ["127.0.0.1:20000", "127.0.0.2:20000", "127.0.0.3:20000"],
        )
        self.assertEqual(
            _collect_query_addresses(cluster, only_standby_slaves=True),
            ["127.0.0.1:20000", "127.0.0.2:20000"],
        )


class TestClusterVariableDiff(unittest.TestCase):
    def test_diff_variables_severity_and_skip(self):
        res = diff_variables(
            {"sql_mode": "STRICT", "wait_timeout": "28800", "server_id": "1"},
            {"sql_mode": "TRADITIONAL", "wait_timeout": "3600", "server_id": "2"},
            high_impact_keys={"sql_mode"},
        )
        self.assertEqual(len(res), 2)
        by_name = {item["variable_name"]: item for item in res}
        self.assertEqual(by_name["sql_mode"]["severity"], "high")
        self.assertEqual(by_name["wait_timeout"]["severity"], "warn")
        self.assertNotIn("server_id", by_name)

    def test_tendbha_ignores_non_standby_and_skips_unreachable(self):
        runtime_data = {
            "master": {
                "address": "127.0.0.1:20000",
                "instance_role": "backend_master",
                "machine_type": "backend",
                "variables": {"sql_mode": "STRICT", "wait_timeout": "28800"},
            },
            "slaves": [
                {
                    "address": "127.0.0.2:20000",
                    "instance_role": "backend_slave",
                    "machine_type": "backend",
                    "is_stand_by": True,
                    "variables": {"sql_mode": "TRADITIONAL", "wait_timeout": "28800"},
                },
                {
                    "address": "127.0.0.3:20000",
                    "instance_role": "backend_slave",
                    "machine_type": "backend",
                    "is_stand_by": False,
                    "variables": {"sql_mode": "OTHER", "wait_timeout": "100"},
                },
                {
                    "address": "127.0.0.4:20000",
                    "instance_role": "backend_slave",
                    "machine_type": "backend",
                    "is_stand_by": True,
                    "variables": None,
                },
            ],
        }
        diff = build_tendbha_variable_diff(runtime_data, cluster_domain="ha.test.db", high_impact_keys={"sql_mode"})
        self.assertEqual(len(diff["replication_pairs"]), 1)
        self.assertEqual(diff["replication_pairs"][0]["slave"], "127.0.0.2:20000")
        self.assertEqual(diff["replication_pairs"][0]["mismatches"][0]["variable_name"], "sql_mode")

    def test_tendbcluster_spider_and_shard_group_aggregation(self):
        runtime_data = {
            "spiders": [
                {
                    "address": "127.0.0.10:25000",
                    "instance_role": "spider_master",
                    "machine_type": "spider",
                    "version": "tspider-3.7.5",
                    "variables": {"spider_bgs_mode": "1", "sql_mode": "STRICT"},
                },
                {
                    "address": "127.0.0.11:25000",
                    "instance_role": "spider_master",
                    "machine_type": "spider",
                    "version": "tspider-3.7.8",
                    "variables": {"spider_bgs_mode": "0", "sql_mode": "STRICT"},
                },
            ],
            "shards": {
                "0": {
                    "master": {
                        "address": "127.0.0.20:20000",
                        "instance_role": "remote_master",
                        "machine_type": "remote",
                        "variables": {"character_set_server": "utf8mb4"},
                    },
                    "slave": {
                        "address": "127.0.0.21:20000",
                        "instance_role": "remote_slave",
                        "machine_type": "remote",
                        "variables": {"character_set_server": "utf8"},
                    },
                },
                "1": {
                    "master": {
                        "address": "127.0.0.22:20000",
                        "instance_role": "remote_master",
                        "machine_type": "remote",
                        "variables": {"character_set_server": "utf8mb4"},
                    },
                    "slave": {
                        "address": "127.0.0.23:20000",
                        "instance_role": "remote_slave",
                        "machine_type": "remote",
                        "variables": {"character_set_server": "utf8"},
                    },
                },
            },
        }
        diff = build_tendbcluster_variable_diff(
            runtime_data,
            cluster_domain="spider.test.db",
            spider_high_impact_keys={"spider_bgs_mode"},
            shard_high_impact_keys={"character_set_server"},
        )
        self.assertFalse(diff["spider_version"]["consistent"])
        self.assertEqual(len(diff["spider_groups"]), 1)
        self.assertEqual(diff["spider_groups"][0]["mismatches"][0]["variable_name"], "spider_bgs_mode")
        self.assertEqual(diff["spider_groups"][0]["mismatches"][0]["severity"], "high")
        self.assertEqual(len(diff["shard_pairs"]), 1)
        self.assertEqual(diff["shard_pairs"][0]["scope"], "shard_group")
        self.assertEqual(diff["shard_pairs"][0]["affected_shards"], ["0", "1"])
        self.assertNotIn("remote_master_mismatches", diff)

    def test_bool_normalization_and_absent_detection(self):
        # ON vs 1 归一一致；rocksdb_large_prefix 双侧缺失跳过；innodb_large_prefix 单边缺失报 ABSENT
        res = diff_variables(
            {"innodb_strict_mode": "ON", "innodb_large_prefix": "ON"},
            {"innodb_strict_mode": "1"},
            high_impact_keys={"innodb_strict_mode", "innodb_large_prefix"},
            bool_keys={"innodb_strict_mode", "innodb_large_prefix"},
            check_absent_keys={"innodb_strict_mode", "innodb_large_prefix", "rocksdb_large_prefix"},
        )
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["variable_name"], "innodb_large_prefix")
        self.assertEqual(res[0]["master_value"], "ON")
        self.assertEqual(res[0]["slave_value"], "ABSENT")
        self.assertEqual(res[0]["severity"], "high")

    def test_spider_slave_ignored_and_remote_master_group_diff(self):
        runtime_data = {
            "spiders": [
                {
                    "address": "127.0.0.10:25000",
                    "instance_role": "spider_master",
                    "machine_type": "spider",
                    "version": "tspider-3.7.8",
                    "variables": {"sql_mode": "STRICT"},
                },
                {
                    "address": "127.0.0.11:25000",
                    "instance_role": "spider_master",
                    "machine_type": "spider",
                    "version": "tspider-3.7.8",
                    "variables": {"sql_mode": "STRICT"},
                },
                {
                    "address": "127.0.0.12:25000",
                    "instance_role": "spider_slave",
                    "machine_type": "spider",
                    "version": "tspider-3.6.0",
                    "variables": {"sql_mode": "OTHER"},
                },
            ],
            "shards": {
                "0": {
                    "master": {
                        "address": "127.0.0.20:20000",
                        "instance_role": "remote_master",
                        "machine_type": "remote",
                        "variables": {"innodb_large_prefix": "ON", "sql_mode": "STRICT"},
                    },
                    "slave": {
                        "address": "127.0.0.21:20000",
                        "instance_role": "remote_slave",
                        "machine_type": "remote",
                        "variables": {"innodb_large_prefix": "1", "sql_mode": "STRICT"},
                    },
                },
                "1": {
                    "master": {
                        "address": "127.0.0.22:20000",
                        "instance_role": "remote_master",
                        "machine_type": "remote",
                        "variables": {"innodb_large_prefix": "OFF", "sql_mode": "STRICT"},
                    },
                    "slave": {
                        "address": "127.0.0.23:20000",
                        "instance_role": "remote_slave",
                        "machine_type": "remote",
                        "variables": {"innodb_large_prefix": "0", "sql_mode": "STRICT"},
                    },
                },
            },
        }
        diff = build_tendbcluster_variable_diff(
            runtime_data,
            cluster_domain="spider.cross.db",
            shard_high_impact_keys={"innodb_large_prefix"},
            bool_keys={"innodb_large_prefix"},
            shard_check_absent_keys={"innodb_large_prefix", "rocksdb_large_prefix"},
            include_remote_master_group=True,
        )
        # spider_slave 被彻底忽略：版本一致、无 spider 差异
        self.assertTrue(diff["spider_version"]["consistent"])
        self.assertEqual(
            diff["spider_version"]["by_version"], {"tspider-3.7.8": ["127.0.0.10:25000", "127.0.0.11:25000"]}
        )
        self.assertEqual(diff["spider_groups"], [])
        # 分片内主从 ON vs 1 / OFF vs 0 归一化后一致
        self.assertEqual(diff["shard_pairs"], [])
        # 跨分片 remote_master 检出 innodb_large_prefix 漂移
        self.assertEqual(len(diff["remote_master_mismatches"]), 1)
        rm_item = diff["remote_master_mismatches"][0]
        self.assertEqual(rm_item["variable_name"], "innodb_large_prefix")
        self.assertEqual(rm_item["severity"], "high")
        self.assertEqual(rm_item["by_value"], {"ON": ["127.0.0.20:20000"], "OFF": ["127.0.0.22:20000"]})

    def test_build_spider_version_prefers_runtime_and_skips_unreachable(self):
        runtime_data = {
            "spiders": [
                {
                    "address": "127.0.0.10:25000",
                    "instance_role": "spider_master",
                    "version": "tspider-3.7.8",
                    "variables": {"version": "5.7.20-tspider-3.7.8-log"},
                },
                {
                    "address": "127.0.0.11:25000",
                    "instance_role": "spider_master",
                    "version": "tspider-3.7.8",
                    "variables": {"version": "5.7.20-tspider-3.7.9-log"},
                },
                {
                    "address": "127.0.0.12:25000",
                    "instance_role": "spider_master",
                    "version": "tspider-3.6.0",
                    "variables": None,
                },
            ]
        }
        # 巡检模式：优先比运行时 version 且跳过失联节点 127.0.0.12
        inspect_ver = build_spider_version(
            runtime_data,
            prefer_runtime_version=True,
            skip_missing_vars=True,
        )
        self.assertFalse(inspect_ver["consistent"])
        self.assertEqual(
            inspect_ver["by_version"],
            {
                "5.7.20-tspider-3.7.8-log": ["127.0.0.10:25000"],
                "5.7.20-tspider-3.7.9-log": ["127.0.0.11:25000"],
            },
        )
        # MCP 默认模式：保留原行为（优先元数据 proxy.version）
        mcp_ver = build_spider_version(runtime_data)
        self.assertFalse(mcp_ver["consistent"])
        self.assertIn("tspider-3.7.8", mcp_ver["by_version"])
        self.assertIn("tspider-3.6.0", mcp_ver["by_version"])

    def test_semantic_normalization_charset_sql_mode_isolation_and_engine(self):
        # 等价写法全部判一致：utf8/utf8mb3、同后缀排序规则、sql_mode 乱序、隔离级别 _/-、存储引擎大小写
        eq_res = diff_variables(
            {
                "character_set_server": "utf8",
                "collation_server": "utf8_general_ci",
                "sql_mode": "STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION",
                "transaction_isolation": "REPEATABLE_READ",
                "tx_isolation": "READ_COMMITTED",
                "default_storage_engine": "InnoDB",
            },
            {
                "character_set_server": "UTF8MB3",
                "collation_server": "utf8mb3_general_ci",
                "sql_mode": "no_engine_substitution, STRICT_TRANS_TABLES",
                "transaction_isolation": "REPEATABLE-READ",
                "tx_isolation": "read-committed",
                "default_storage_engine": "innodb",
            },
            semantic_normalize=True,
        )
        self.assertEqual(eq_res, [])

        # 非等价写法必须报差异：utf8 vs utf8mb4、utf8_bin vs utf8mb3_general_ci、sql_mode 少项
        neq_res = diff_variables(
            {
                "character_set_server": "utf8",
                "collation_server": "utf8_bin",
                "sql_mode": "STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION",
            },
            {
                "character_set_server": "utf8mb4",
                "collation_server": "utf8mb3_general_ci",
                "sql_mode": "STRICT_TRANS_TABLES",
            },
            semantic_normalize=True,
        )
        self.assertEqual(
            [item["variable_name"] for item in neq_res],
            ["character_set_server", "collation_server", "sql_mode"],
        )
