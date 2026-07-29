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

from backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables import (
    _apply_spider_variable_filter,
    _apply_storage_engine_filter,
    _filter_variables,
    _query_variables_for_addresses,
)


def _rows(*pairs):
    return [{"Variable_name": name, "Value": value} for name, value in pairs]


def _drs_item(address, variables, error_msg=""):
    return {
        "address": address,
        "error_msg": error_msg,
        "cmd_results": [
            {
                "error_msg": "",
                "table_data": [{"Variable_name": k, "Value": v} for k, v in variables.items()],
            }
        ],
    }


class TestFilterVariables:
    def test_ssl_prefix_filtered(self):
        result = _filter_variables(
            _rows(
                ("ssl_cipher", "AES"),
                ("ssl_ca", "/etc/ssl/ca.pem"),
                ("max_connections", "1000"),
            )
        )
        assert "ssl_cipher" not in result
        assert "ssl_ca" not in result
        assert result["max_connections"] == "1000"

    def test_report_prefix_filtered(self):
        result = _filter_variables(
            _rows(
                ("report_host", "127.0.0.1"),
                ("report_port", "3306"),
                ("max_connections", "1000"),
            )
        )
        assert "report_host" not in result
        assert "report_port" not in result
        assert result["max_connections"] == "1000"

    def test_low_value_innodb_filtered_high_value_kept(self):
        result = _filter_variables(
            _rows(
                ("innodb_ft_min_token_size", "3"),
                ("innodb_api_enable_binlog", "OFF"),
                ("innodb_monitor_enable", "all"),
                ("innodb_buffer_pool_dump_at_shutdown", "ON"),
                ("innodb_buffer_pool_load_at_startup", "ON"),
                ("innodb_version", "5.7.20"),
                ("innodb_buffer_pool_filename", "ib_buffer_pool"),
                ("innodb_file_format_check", "ON"),
                ("innodb_file_format_max", "Barracuda"),
                ("innodb_support_xa", "ON"),
                ("innodb_buffer_pool_size", "1073741824"),
                ("innodb_io_capacity", "2000"),
            )
        )
        assert "innodb_ft_min_token_size" not in result
        assert "innodb_api_enable_binlog" not in result
        assert "innodb_monitor_enable" not in result
        assert "innodb_buffer_pool_dump_at_shutdown" not in result
        assert "innodb_buffer_pool_load_at_startup" not in result
        assert "innodb_version" not in result
        assert "innodb_buffer_pool_filename" not in result
        assert "innodb_file_format_check" not in result
        assert "innodb_file_format_max" not in result
        assert "innodb_support_xa" not in result
        assert result["innodb_buffer_pool_size"] == "1073741824"
        assert result["innodb_io_capacity"] == "2000"


class TestQueryVariablesAddressMapping:
    @patch("backend.dbm_aiagent.mcp_tools.mysql.impl.cluster_runtime_variables.DRSApi.v2_mysql_rpc")
    def test_maps_by_response_address_not_request_order(self, mock_rpc):
        """DRS 返回顺序与请求不一致时，必须按 address 对齐，避免把存储参数挂到 Spider。"""
        spider = "127.0.0.2:25000"
        remote = "127.0.0.3:20000"
        # 请求顺序：spider, remote；返回顺序故意反过来
        mock_rpc.return_value = [
            _drs_item(remote, {"back_log": "30000", "max_connections": "3000"}),
            _drs_item(spider, {"back_log": "100", "max_connections": "2000"}),
        ]

        addr_to_variables, unused_meta = _query_variables_for_addresses(bk_cloud_id=0, addresses=[spider, remote])

        assert addr_to_variables[spider]["back_log"] == "100"
        assert addr_to_variables[remote]["back_log"] == "30000"
        assert addr_to_variables[spider]["max_connections"] == "2000"


class TestSpiderVariableFilter:
    def test_strip_storage_and_replication_prefixes(self):
        variables = {
            "innodb_buffer_pool_size": "1G",
            "slave_net_timeout": "60",
            "relay_log": "relay-bin",
            "relay_log_basename": "/data/relay",
            "replicate_do_db": "db1",
            "rpl_semi_sync_master_enabled": "ON",
            "rpl_semi_sync_slave_enabled": "ON",
            "spider_auto_increment_mode_switch": "1",
            "max_connections": "2000",
        }
        result = _apply_spider_variable_filter(variables)
        assert "innodb_buffer_pool_size" not in result
        assert "slave_net_timeout" not in result
        assert "relay_log" not in result
        assert "relay_log_basename" not in result
        assert "replicate_do_db" not in result
        assert "rpl_semi_sync_master_enabled" not in result
        assert "rpl_semi_sync_slave_enabled" not in result
        assert result["spider_auto_increment_mode_switch"] == "1"
        assert result["max_connections"] == "2000"


class TestStorageEngineFilter:
    def test_innodb_keeps_innodb_vars(self):
        variables = {
            "default_storage_engine": "InnoDB",
            "innodb_buffer_pool_size": "1G",
            "max_connections": "1000",
        }
        result = _apply_storage_engine_filter(variables)
        assert result["innodb_buffer_pool_size"] == "1G"
        assert result["default_storage_engine"] == "InnoDB"

    def test_non_innodb_strips_all_innodb(self):
        variables = {
            "default_storage_engine": "RocksDB",
            "innodb_buffer_pool_size": "1G",
            "innodb_io_capacity": "2000",
            "max_connections": "1000",
        }
        result = _apply_storage_engine_filter(variables)
        assert "innodb_buffer_pool_size" not in result
        assert "innodb_io_capacity" not in result
        assert result["default_storage_engine"] == "RocksDB"
        assert result["max_connections"] == "1000"

    def test_missing_engine_keeps_innodb(self):
        variables = {
            "innodb_buffer_pool_size": "1G",
            "max_connections": "1000",
        }
        result = _apply_storage_engine_filter(variables)
        assert result["innodb_buffer_pool_size"] == "1G"
        assert result["max_connections"] == "1000"
