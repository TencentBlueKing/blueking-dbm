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
from django.test import SimpleTestCase

from backend.flow.utils.mysql.mysql_commom_query import (
    ROCKSDB_PLUGIN_LOAD,
    extract_spider_semantic_configs,
    extract_storage_semantic_configs,
    extract_tdbctl_semantic_configs,
    get_mysql_start_configs,
)


def _base_common_vars(**extra):
    data = {
        "sql_mode": "STRICT_TRANS_TABLES",
        "lower_case_table_names": "0",
        "character_set_server": "utf8mb4",
        "collation_server": "utf8mb4_general_ci",
        # 以下为会话级变量，show global variables 会返回，但不可写入 my.cnf
        "character_set_client": "utf8mb4",
        "character_set_connection": "utf8mb4",
        "collation_connection": "utf8mb4_general_ci",
        "character_set_database": "utf8mb4",
        "collation_database": "utf8mb4_general_ci",
        "foreign_key_checks": "ON",
        "sql_safe_updates": "OFF",
        "default_storage_engine": "InnoDB",
        "default_tmp_storage_engine": "InnoDB",
        "explicit_defaults_for_timestamp": "ON",
        "log_bin_trust_function_creators": "ON",
        "default_time_zone": "+08:00",
        "max_allowed_packet": "134217728",
        "wait_timeout": "86400",
        "interactive_timeout": "86400",
        "group_concat_max_len": "1024",
        "sql_require_primary_key": "OFF",
        "sql_generate_invisible_primary_key": "OFF",
        "innodb_file_per_table": "ON",
        "innodb_strict_mode": "ON",
        "innodb_lock_wait_timeout": "50",
        "innodb_online_alter_log_max_size": "134217728",
        "rocksdb_large_prefix": "ON",
        "rocksdb_strict_collation_check": "ON",
        "rocksdb_strict_collation_exceptions": ".*",
        "rocksdb_lock_wait_timeout": "1",
        "tokudb_lock_timeout": "4000",
        "tokudb_row_format": "tokudb_zlib",
        "socket": "/tmp/mysql.sock",
        "datadir": "/data/mysql",
    }
    data.update(extra)
    return data


class TestExtractStorageSemanticConfigs(SimpleTestCase):
    """存储层语义启动配置：按 default_storage_engine 门控"""

    def test_innodb_includes_innodb_excludes_rocks_toku(self):
        result = extract_storage_semantic_configs(_base_common_vars())
        self.assertEqual(result["default_storage_engine"], "InnoDB")
        self.assertEqual(result["innodb_file_per_table"], "ON")
        self.assertEqual(result["innodb_online_alter_log_max_size"], "134217728")
        self.assertEqual(result["loose_sql_require_primary_key"], "OFF")
        self.assertEqual(result["loose_sql_generate_invisible_primary_key"], "OFF")
        self.assertNotIn("sql_require_primary_key", result)
        self.assertNotIn("sql_generate_invisible_primary_key", result)
        self.assertNotIn("rocksdb_large_prefix", result)
        self.assertNotIn("tokudb_lock_timeout", result)
        self.assertNotIn("socket", result)
        self.assertNotIn("datadir", result)

    def test_session_only_vars_never_extracted(self):
        """会话级变量写进 my.cnf 会导致 mysqld unknown variable 启动失败"""
        result = extract_storage_semantic_configs(_base_common_vars())
        for name in [
            "character_set_client",
            "character_set_connection",
            "collation_connection",
            "character_set_database",
            "collation_database",
            "foreign_key_checks",
            "sql_safe_updates",
        ]:
            self.assertNotIn(name, result)

    def test_rocksdb_includes_rocks_excludes_innodb(self):
        result = extract_storage_semantic_configs(_base_common_vars(default_storage_engine="RocksDB"))
        self.assertEqual(result["rocksdb_large_prefix"], "ON")
        self.assertEqual(result["rocksdb_lock_wait_timeout"], "1")
        self.assertEqual(result["rocksdb_strict_collation_exceptions"], ".*")
        self.assertEqual(result["plugin-load"], ROCKSDB_PLUGIN_LOAD)
        self.assertNotIn("loose_rocksdb_large_prefix", result)
        self.assertNotIn("innodb_file_per_table", result)
        self.assertNotIn("innodb_online_alter_log_max_size", result)
        self.assertNotIn("tokudb_lock_timeout", result)

    def test_non_rocksdb_engine_excludes_plugin_load(self):
        for engine in ("InnoDB", "TokuDB", "MyISAM"):
            result = extract_storage_semantic_configs(_base_common_vars(default_storage_engine=engine))
            self.assertNotIn("plugin-load", result)

    def test_tokudb_includes_toku_excludes_innodb(self):
        result = extract_storage_semantic_configs(_base_common_vars(default_storage_engine="TokuDB"))
        self.assertEqual(result["tokudb_lock_timeout"], "4000")
        self.assertEqual(result["tokudb_row_format"], "tokudb_zlib")
        self.assertNotIn("loose_tokudb_lock_timeout", result)
        self.assertNotIn("innodb_file_per_table", result)
        self.assertNotIn("rocksdb_large_prefix", result)

    def test_unknown_engine_only_common(self):
        result = extract_storage_semantic_configs(_base_common_vars(default_storage_engine="MyISAM"))
        self.assertEqual(result["sql_mode"], "STRICT_TRANS_TABLES")
        self.assertEqual(result["default_storage_engine"], "MyISAM")
        self.assertNotIn("innodb_file_per_table", result)
        self.assertNotIn("rocksdb_large_prefix", result)
        self.assertNotIn("tokudb_lock_timeout", result)

    def test_missing_vars_only_copy_existing_keys(self):
        result = extract_storage_semantic_configs(
            {
                "default_storage_engine": "InnoDB",
                "sql_mode": "",
                "innodb_file_per_table": "ON",
            }
        )
        self.assertEqual(set(result.keys()), {"default_storage_engine", "sql_mode", "innodb_file_per_table"})

    def test_tmp_engine_does_not_gate_branch(self):
        """default_tmp_storage_engine 可同步，但不参与引擎门控"""
        result = extract_storage_semantic_configs(
            _base_common_vars(
                default_storage_engine="RocksDB",
                default_tmp_storage_engine="InnoDB",
            )
        )
        self.assertEqual(result["default_tmp_storage_engine"], "InnoDB")
        self.assertIn("rocksdb_large_prefix", result)
        self.assertNotIn("innodb_file_per_table", result)

    def test_engine_name_case_and_space_insensitive(self):
        result = extract_storage_semantic_configs(_base_common_vars(default_storage_engine="  rocksdb "))
        self.assertIn("rocksdb_large_prefix", result)
        self.assertNotIn("innodb_file_per_table", result)

    def test_get_mysql_start_configs_delegates_to_storage_extractor(self):
        var_map = _base_common_vars(default_storage_engine="TokuDB")
        self.assertEqual(get_mysql_start_configs(var_map), extract_storage_semantic_configs(var_map))

    def test_version_only_vars_skipped_when_absent(self):
        """8.0+ 补丁级项缺省时不报错、不写入（含 loose_ 前缀）"""
        var_map = _base_common_vars()
        var_map.pop("sql_require_primary_key", None)
        var_map.pop("sql_generate_invisible_primary_key", None)
        result = extract_storage_semantic_configs(var_map)
        self.assertNotIn("sql_require_primary_key", result)
        self.assertNotIn("sql_generate_invisible_primary_key", result)
        self.assertNotIn("loose_sql_require_primary_key", result)
        self.assertNotIn("loose_sql_generate_invisible_primary_key", result)
        self.assertIn("sql_mode", result)

    def test_mysql80_patch_vars_emitted_with_loose_prefix(self):
        """粗粒度 8.0 仿真镜像可能低于源补丁；必须 loose_ 避免 unknown variable CrashLoop"""
        result = extract_storage_semantic_configs(_base_common_vars())
        self.assertEqual(result["loose_sql_require_primary_key"], "OFF")
        self.assertEqual(result["loose_sql_generate_invisible_primary_key"], "OFF")
        self.assertNotIn("sql_require_primary_key", result)
        self.assertNotIn("sql_generate_invisible_primary_key", result)


class TestExtractSpiderSemanticConfigs(SimpleTestCase):
    """Spider：公共默认参数 + Spider 专用白名单，不含引擎参数与连接池参数"""

    def test_spider_includes_common_and_spider_vars_excludes_engine(self):
        var_map = _base_common_vars(
            spider_net_read_timeout="600",
            spider_bgs_mode="1",
            spider_support_xa="ON",
            spider_internal_xa="OFF",
            ddl_execute_by_ctl="ON",
            spider_query_one_shard="OFF",
            spider_transaction_one_shard="OFF",
            spider_max_connections="200",
            spider_index_hint_pushdown="ON",
        )
        result = extract_spider_semantic_configs(var_map)
        self.assertEqual(result["sql_mode"], "STRICT_TRANS_TABLES")
        self.assertEqual(result["default_storage_engine"], "InnoDB")
        self.assertEqual(result["loose_spider_net_read_timeout"], "600")
        self.assertEqual(result["loose_spider_bgs_mode"], "1")
        self.assertEqual(result["loose_spider_support_xa"], "ON")
        self.assertEqual(result["loose_spider_internal_xa"], "OFF")
        self.assertEqual(result["loose_ddl_execute_by_ctl"], "ON")
        self.assertEqual(result["loose_spider_query_one_shard"], "OFF")
        self.assertEqual(result["loose_spider_transaction_one_shard"], "OFF")
        self.assertEqual(result["loose_spider_index_hint_pushdown"], "ON")
        self.assertNotIn("spider_max_connections", result)
        self.assertNotIn("loose_spider_max_connections", result)
        self.assertNotIn("character_set_connection", result)
        self.assertNotIn("innodb_file_per_table", result)
        self.assertNotIn("loose_rocksdb_large_prefix", result)
        self.assertNotIn("loose_tokudb_lock_timeout", result)
        self.assertNotIn("socket", result)

    def test_spider_only_common_when_spider_vars_absent(self):
        result = extract_spider_semantic_configs(_base_common_vars())
        self.assertEqual(result["character_set_server"], "utf8mb4")
        self.assertNotIn("loose_spider_net_read_timeout", result)
        self.assertNotIn("innodb_strict_mode", result)
        self.assertNotIn("loose_ddl_execute_by_ctl", result)


class TestExtractTdbctlSemanticConfigs(SimpleTestCase):
    """Tdbctl：存储层策略 + tc_* 语义白名单；不抽 tc_admin / wrapper 前缀"""

    def test_tdbctl_includes_storage_and_tc_vars_excludes_tc_admin(self):
        var_map = _base_common_vars(
            tc_admin="ON",
            tc_ignore_partitioning_for_create_table="ON",
            tc_force_execute="ON",
            tc_enable_autoinc_check="ON",
            tc_partition_admin="ON",
            tc_dry_run="OFF",
            tc_enable_internal_dump="ON",
            tc_enable_internal_grant="ON",
            tc_restrict_query_from_spider="ON",
            tc_spider_wrapper_prefix="SPIDER",
            tc_check_availability="OFF",
        )
        result = extract_tdbctl_semantic_configs(var_map)
        self.assertEqual(result["sql_mode"], "STRICT_TRANS_TABLES")
        self.assertEqual(result["innodb_file_per_table"], "ON")
        self.assertEqual(result["loose_tc_ignore_partitioning_for_create_table"], "ON")
        self.assertEqual(result["loose_tc_force_execute"], "ON")
        self.assertEqual(result["loose_tc_dry_run"], "OFF")
        self.assertEqual(result["loose_tc_restrict_query_from_spider"], "ON")
        self.assertNotIn("tc_admin", result)
        self.assertNotIn("loose_tc_admin", result)
        self.assertNotIn("loose_tc_spider_wrapper_prefix", result)
        self.assertNotIn("loose_tc_check_availability", result)
        self.assertNotIn("socket", result)

    def test_tdbctl_without_tc_vars_equals_storage_extractor(self):
        var_map = _base_common_vars()
        self.assertEqual(extract_tdbctl_semantic_configs(var_map), extract_storage_semantic_configs(var_map))
