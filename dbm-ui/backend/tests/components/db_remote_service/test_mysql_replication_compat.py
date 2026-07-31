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
from unittest.mock import MagicMock, patch

from backend.components.db_remote_service.mysql_replication_compat import (  # pylint: disable=protected-access
    _map_row_fields,
    _translate_change_master_params,
    _translate_single_cmd,
    get_instance_major_version,
    map_result_fields,
    translate_cmds,
)

"""MySQL 8.4 复制语法兼容模块单元测试"""


class TestTranslateCmds:
    """测试 translate_cmds 函数"""

    def test_version_below_84_no_translation(self):
        """版本 < 8.4 时不翻译"""
        cmds = ["show slave status", "start slave", "CHANGE MASTER TO MASTER_HOST='1.1.1.1'"]
        translated, indices = translate_cmds(cmds, (5, 7))
        assert translated == cmds
        assert indices == []

    def test_version_80_no_translation(self):
        """版本 8.0 时不翻译"""
        cmds = ["show slave status"]
        translated, indices = translate_cmds(cmds, (8, 0))
        assert translated == cmds
        assert indices == []

    def test_version_84_translates_show_slave_status(self):
        """版本 >= 8.4 时翻译 show slave status"""
        cmds = ["show slave status"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["SHOW REPLICA STATUS"]
        assert indices == [0]

    def test_version_84_translates_show_master_status(self):
        """版本 >= 8.4 时翻译 show master status"""
        cmds = ["show master status"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["SHOW BINARY LOG STATUS"]
        assert indices == [0]

    def test_version_84_translates_start_slave(self):
        """版本 >= 8.4 时翻译 start slave"""
        cmds = ["start slave"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["START REPLICA"]
        assert indices == []

    def test_version_84_translates_stop_slave(self):
        """版本 >= 8.4 时翻译 stop slave"""
        cmds = ["stop slave"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["STOP REPLICA"]
        assert indices == []

    def test_version_84_translates_reset_slave(self):
        """版本 >= 8.4 时翻译 reset slave"""
        cmds = ["reset slave"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["RESET REPLICA"]
        assert indices == []

    def test_version_84_translates_reset_slave_all(self):
        """版本 >= 8.4 时翻译 reset slave all，保留 ALL 后缀"""
        cmds = ["reset slave all"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["RESET REPLICA all"]
        assert indices == []

    def test_version_84_translates_reset_master(self):
        """版本 >= 8.4 时翻译 reset master"""
        cmds = ["reset master"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["RESET BINARY LOGS AND GTIDS"]
        assert indices == []

    def test_version_84_translates_show_slave_hosts(self):
        """版本 >= 8.4 时翻译 show slave hosts"""
        cmds = ["show slave hosts"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["SHOW REPLICAS"]
        assert indices == []

    def test_version_84_translates_show_master_logs(self):
        """版本 >= 8.4 时翻译 show master logs"""
        cmds = ["show master logs"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["SHOW BINARY LOGS"]
        assert indices == []

    def test_version_84_translates_purge_master_logs(self):
        """版本 >= 8.4 时翻译 purge master logs，保留后续条件"""
        cmds = ["purge master logs to 'binlog.000010'"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["PURGE BINARY LOGS to 'binlog.000010'"]
        assert indices == []

    def test_version_84_translates_purge_master_logs_before(self):
        """版本 >= 8.4 时翻译 purge master logs before"""
        cmds = ["PURGE MASTER LOGS BEFORE '2024-01-01 00:00:00'"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == ["PURGE BINARY LOGS BEFORE '2024-01-01 00:00:00'"]
        assert indices == []

    def test_version_84_translates_change_master_to(self):
        """版本 >= 8.4 时翻译 CHANGE MASTER TO 及其参数名"""
        cmds = ["CHANGE MASTER TO MASTER_HOST='1.1.1.1', MASTER_PORT=3306, MASTER_AUTO_POSITION=1"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert "CHANGE REPLICATION SOURCE TO" in translated[0]
        assert "SOURCE_HOST" in translated[0]
        assert "SOURCE_PORT" in translated[0]
        assert "SOURCE_AUTO_POSITION" in translated[0]
        assert "MASTER_HOST" not in translated[0]
        assert indices == []

    def test_mixed_cmds_partial_translation(self):
        """混合命令场景：部分翻译、部分不翻译"""
        cmds = ["select 1", "show slave status", "show databases"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated[0] == "select 1"
        assert translated[1] == "SHOW REPLICA STATUS"
        assert translated[2] == "show databases"
        assert indices == [1]

    def test_normal_sql_not_translated(self):
        """普通 SQL 不做任何修改"""
        cmds = ["select 1", "show databases", "show processlist"]
        translated, indices = translate_cmds(cmds, (8, 4))
        assert translated == cmds
        assert indices == []


class TestTranslateSingleCmd:
    """测试 _translate_single_cmd 函数"""

    def test_case_insensitive_show_slave_status(self):
        """大小写不敏感匹配 show slave status"""
        cmd, needs_map = _translate_single_cmd("SHOW SLAVE STATUS")
        assert cmd == "SHOW REPLICA STATUS"
        assert needs_map is True

    def test_case_insensitive_mixed_case(self):
        """混合大小写匹配"""
        cmd, needs_map = _translate_single_cmd("Show Slave Status")
        assert cmd == "SHOW REPLICA STATUS"
        assert needs_map is True

    def test_with_semicolon(self):
        """带分号的命令"""
        cmd, needs_map = _translate_single_cmd("show slave status;")
        assert cmd == "SHOW REPLICA STATUS"
        assert needs_map is True

    def test_with_leading_spaces(self):
        """带前导空格的命令"""
        cmd, needs_map = _translate_single_cmd("  show slave status  ")
        assert cmd == "SHOW REPLICA STATUS"
        assert needs_map is True

    def test_start_slave_with_suffix(self):
        """start slave 带后缀"""
        cmd, needs_map = _translate_single_cmd("start slave;")
        assert cmd == "START REPLICA;"
        assert needs_map is False

    def test_stop_slave_with_suffix(self):
        """stop slave 带后缀"""
        cmd, needs_map = _translate_single_cmd("stop slave;")
        assert cmd == "STOP REPLICA;"
        assert needs_map is False

    def test_unknown_cmd_not_translated(self):
        """未知命令不翻译"""
        cmd, needs_map = _translate_single_cmd("select * from t1")
        assert cmd == "select * from t1"
        assert needs_map is False


class TestTranslateChangeMasterParams:
    """测试 _translate_change_master_params 函数"""

    def test_replaces_all_params(self):
        """替换所有参数名"""
        cmd = (
            "CHANGE REPLICATION SOURCE TO "
            "MASTER_HOST='1.1.1.1', "
            "MASTER_PORT=3306, "
            "MASTER_USER='repl', "
            "MASTER_PASSWORD='pwd', "
            "MASTER_LOG_FILE='binlog.000001', "
            "MASTER_LOG_POS=154, "
            "MASTER_AUTO_POSITION=1"
        )
        result = _translate_change_master_params(cmd)
        assert "SOURCE_HOST" in result
        assert "SOURCE_PORT" in result
        assert "SOURCE_USER" in result
        assert "SOURCE_PASSWORD" in result
        assert "SOURCE_LOG_FILE" in result
        assert "SOURCE_LOG_POS" in result
        assert "SOURCE_AUTO_POSITION" in result
        assert "MASTER_HOST" not in result
        assert "MASTER_PORT" not in result

    def test_case_insensitive_params(self):
        """大小写不敏感替换参数名"""
        cmd = "CHANGE REPLICATION SOURCE TO master_host='1.1.1.1', master_port=3306"
        result = _translate_change_master_params(cmd)
        assert "SOURCE_HOST" in result
        assert "SOURCE_PORT" in result


class TestMapResultFields:
    """测试 map_result_fields 函数"""

    def test_maps_specified_indices_keep_original(self):
        """对指定索引的 cmd_results 做字段映射，默认保留新旧两个字段名"""
        result = [
            {
                "cmd_results": [
                    {
                        "table_data": [
                            {
                                "Replica_IO_Running": "Yes",
                                "Replica_SQL_Running": "Yes",
                                "Seconds_Behind_Source": 0,
                                "Source_Host": "1.1.1.1",
                            }
                        ]
                    }
                ]
            }
        ]
        mapped = map_result_fields(result, [0])
        row = mapped[0]["cmd_results"][0]["table_data"][0]
        # 旧版字段名存在
        assert row["Slave_IO_Running"] == "Yes"
        assert row["Slave_SQL_Running"] == "Yes"
        assert row["Seconds_Behind_Master"] == 0
        assert row["Master_Host"] == "1.1.1.1"
        # 新版字段名也保留（默认 remove_original=False）
        assert row["Replica_IO_Running"] == "Yes"
        assert row["Seconds_Behind_Source"] == 0

    def test_maps_specified_indices_remove_original(self):
        """对指定索引的 cmd_results 做字段映射，remove_original=True 时移除新版字段名"""
        result = [
            {
                "cmd_results": [
                    {
                        "table_data": [
                            {
                                "Replica_IO_Running": "Yes",
                                "Replica_SQL_Running": "Yes",
                                "Seconds_Behind_Source": 0,
                                "Source_Host": "1.1.1.1",
                            }
                        ]
                    }
                ]
            }
        ]
        mapped = map_result_fields(result, [0], remove_original=True)
        row = mapped[0]["cmd_results"][0]["table_data"][0]
        assert row["Slave_IO_Running"] == "Yes"
        assert row["Slave_SQL_Running"] == "Yes"
        assert row["Seconds_Behind_Master"] == 0
        assert row["Master_Host"] == "1.1.1.1"
        # 新版字段名已移除
        assert "Replica_IO_Running" not in row
        assert "Seconds_Behind_Source" not in row

    def test_does_not_map_unspecified_indices(self):
        """不对未指定索引的 cmd_results 做映射"""
        result = [
            {
                "cmd_results": [
                    {"table_data": [{"Variable_name": "version", "Value": "8.4.0"}]},
                    {"table_data": [{"Replica_IO_Running": "Yes"}]},
                ]
            }
        ]
        mapped = map_result_fields(result, [1])
        # 索引 0 不映射
        assert mapped[0]["cmd_results"][0]["table_data"][0]["Variable_name"] == "version"
        # 索引 1 映射（默认保留新旧两个字段名）
        assert mapped[0]["cmd_results"][1]["table_data"][0]["Slave_IO_Running"] == "Yes"
        assert mapped[0]["cmd_results"][1]["table_data"][0]["Replica_IO_Running"] == "Yes"

    def test_empty_field_map_indices(self):
        """空索引列表不做任何映射"""
        result = [{"cmd_results": [{"table_data": [{"Replica_IO_Running": "Yes"}]}]}]
        mapped = map_result_fields(result, [])
        assert mapped[0]["cmd_results"][0]["table_data"][0]["Replica_IO_Running"] == "Yes"

    def test_multiple_addresses(self):
        """多个地址的结果都做映射"""
        result = [
            {"cmd_results": [{"table_data": [{"Replica_IO_Running": "Yes"}]}]},
            {"cmd_results": [{"table_data": [{"Replica_IO_Running": "No"}]}]},
        ]
        mapped = map_result_fields(result, [0])
        assert mapped[0]["cmd_results"][0]["table_data"][0]["Slave_IO_Running"] == "Yes"
        assert mapped[0]["cmd_results"][0]["table_data"][0]["Replica_IO_Running"] == "Yes"
        assert mapped[1]["cmd_results"][0]["table_data"][0]["Slave_IO_Running"] == "No"
        assert mapped[1]["cmd_results"][0]["table_data"][0]["Replica_IO_Running"] == "No"


class TestMapRowFields:
    """测试 _map_row_fields 函数"""

    def test_maps_known_fields_keep_original(self):
        """映射已知的新版字段名，默认保留新旧两个字段名"""
        row = {"Replica_IO_Running": "Yes", "Source_Host": "1.1.1.1"}
        mapped = _map_row_fields(row)
        # 新旧都保留
        assert mapped["Slave_IO_Running"] == "Yes"
        assert mapped["Master_Host"] == "1.1.1.1"
        assert mapped["Replica_IO_Running"] == "Yes"
        assert mapped["Source_Host"] == "1.1.1.1"

    def test_maps_known_fields_remove_original(self):
        """映射已知的新版字段名，remove_original=True 时只保留旧版"""
        row = {"Replica_IO_Running": "Yes", "Source_Host": "1.1.1.1"}
        mapped = _map_row_fields(row, remove_original=True)
        assert mapped == {"Slave_IO_Running": "Yes", "Master_Host": "1.1.1.1"}

    def test_preserves_unknown_fields(self):
        """保留未知字段名"""
        row = {"Replica_IO_Running": "Yes", "Last_IO_Error": ""}
        mapped = _map_row_fields(row)
        assert mapped["Slave_IO_Running"] == "Yes"
        assert mapped["Replica_IO_Running"] == "Yes"
        assert mapped["Last_IO_Error"] == ""

    def test_already_old_format_preserved(self):
        """已经是旧版格式的字段名保持不变（不在映射表中，原样保留）"""
        row = {"Slave_IO_Running": "Yes", "Master_Host": "1.1.1.1"}
        mapped = _map_row_fields(row)
        assert mapped == {"Slave_IO_Running": "Yes", "Master_Host": "1.1.1.1"}


class TestGetInstanceMajorVersion:
    """测试 get_instance_major_version 函数"""

    @patch("backend.components.db_remote_service.mysql_replication_compat.cache")
    def test_returns_cached_version(self, mock_cache):
        """缓存命中时直接返回"""
        mock_cache.get.return_value = (8, 4)
        version = get_instance_major_version("1.1.1.1:3306")
        assert version == (8, 4)
        mock_cache.set.assert_not_called()

    @patch("backend.components.db_remote_service.mysql_replication_compat.cache")
    @patch("backend.db_meta.models.StorageInstance.objects")
    def test_queries_db_and_caches(self, mock_objects, mock_cache):
        """缓存未命中时查询数据库 StorageInstance.version 并缓存"""
        mock_cache.get.return_value = None

        mock_inst = MagicMock()
        mock_inst.version = "8.4.0"
        mock_objects.get.return_value = mock_inst

        version = get_instance_major_version("1.1.1.1:3306")
        assert version == (8, 4)
        mock_cache.set.assert_called_once()

    @patch("backend.components.db_remote_service.mysql_replication_compat.cache")
    @patch("backend.db_meta.models.StorageInstance.objects")
    def test_queries_db_version_57(self, mock_objects, mock_cache):
        """StorageInstance.version 为 5.7.20 时返回 (5, 7)"""
        mock_cache.get.return_value = None

        mock_inst = MagicMock()
        mock_inst.version = "5.7.20"
        mock_objects.get.return_value = mock_inst

        version = get_instance_major_version("1.1.1.1:3306")
        assert version == (5, 7)
        mock_cache.set.assert_called_once()

    @patch("backend.components.db_remote_service.mysql_replication_compat.cache")
    @patch("backend.db_meta.models.StorageInstance.objects")
    def test_queries_db_version_empty(self, mock_objects, mock_cache):
        """StorageInstance.version 为空时返回默认 (5, 7)"""
        mock_cache.get.return_value = None

        mock_inst = MagicMock()
        mock_inst.version = ""
        mock_objects.get.return_value = mock_inst

        version = get_instance_major_version("1.1.1.1:3306")
        assert version == (5, 7)
        mock_cache.set.assert_called_once()

    @patch("backend.components.db_remote_service.mysql_replication_compat.cache")
    @patch("backend.db_meta.models.StorageInstance.objects")
    def test_returns_default_on_exception(self, mock_objects, mock_cache):
        """查询异常时返回默认版本 (5, 7)"""
        mock_cache.get.return_value = None
        mock_objects.get.side_effect = Exception("not found")

        version = get_instance_major_version("1.1.1.1:3306")
        assert version == (5, 7)
        mock_cache.set.assert_called_once()
