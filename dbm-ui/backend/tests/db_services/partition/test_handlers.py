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

import pytest

from backend.db_meta.enums import ClusterType
from backend.db_services.partition.exceptions import DBPartitionInvalidFieldException
from backend.db_services.partition.handlers import PartitionHandler

pytestmark = pytest.mark.django_db


class TestPartitionHandler:
    """测试 PartitionHandler 类"""

    def test_format_err_execute_objects(self):
        """测试格式化错误执行对象"""
        config_data = {"id": 1, "dblike": "test_db%", "tblike": "test_table%"}
        result = PartitionHandler.format_err_execute_objects(config_data, "error message")
        assert len(result) == 1
        assert result[0]["message"] == "error message"
        assert result[0]["execute_objects"][0]["config_id"] == 1

    def test_format_err_execute_objects_empty(self):
        """测试格式化错误执行对象 - 空数据"""
        result = PartitionHandler.format_err_execute_objects(None, "error")
        assert len(result) == 1
        assert result[0]["execute_objects"][0]["config_id"] is None

    @patch("backend.db_services.partition.handlers.DBPartitionApi.query_conf")
    def test_get_dry_run_data_success(self, mock_query):
        """测试获取dry_run数据 - 成功"""
        params = {"params": {"config_id": 1, "cluster_type": "mysql", "bk_biz_id": 1}}
        res = {"result": True, "data": [{"db": "test", "table": "test_table"}]}

        result = PartitionHandler.get_dry_run_data((params, res))
        assert 1 in result
        assert len(result[1]) == 1

    @patch("backend.db_services.partition.handlers.DBPartitionApi.query_conf")
    def test_get_dry_run_data_failure(self, mock_query):
        """测试获取dry_run数据 - 失败"""
        params = {"params": {"config_id": 1, "cluster_type": "mysql", "bk_biz_id": 1}}
        res = {"result": False, "message": "error"}
        mock_query.return_value = {"count": 1, "items": [{"id": 1, "dblike": "test%", "tblike": "table%"}]}

        result = PartitionHandler.get_dry_run_data((params, res))
        assert 1 in result
        assert result[1][0]["message"] == "error"

    @patch("backend.db_services.partition.handlers.DBPartitionApi.create_conf")
    @patch("backend.db_services.partition.handlers.request_multi_thread")
    @patch("backend.db_services.partition.handlers.Cluster.objects.get")
    @patch("backend.db_services.partition.handlers.PartitionHandler.verify_partition_field")
    @patch("backend.db_services.partition.handlers.PartitionHandler.execute_partition")
    def test_create_and_dry_run_partition(
        self, mock_execute, mock_verify, mock_cluster, mock_multi_thread, mock_create
    ):
        """测试创建并执行分区策略"""
        mock_cluster.return_value = MagicMock(bk_cloud_id=0, id=1)
        mock_create.return_value = {"config_ids": [1, 2]}
        mock_multi_thread.return_value = [{1: []}, {2: []}]
        mock_execute.return_value = [{"ticket_id": 1}]

        create_data = {
            "bk_biz_id": 1,
            "cluster_id": 1,
            "dblikes": ["test%"],
            "tblikes": ["table%"],
            "partition_column": "id",
            "partition_column_type": "int",
        }
        PartitionHandler.create_and_dry_run_partition("admin", create_data)
        assert mock_verify.called
        assert mock_execute.called

    @patch("backend.db_services.partition.handlers.Cluster.objects.get")
    @patch("backend.db_services.partition.handlers.Ticket.create_ticket")
    def test_execute_partition(self, mock_create_ticket, mock_cluster):
        """测试执行分区策略"""
        mock_cluster.return_value = MagicMock(
            id=1, cluster_type=ClusterType.TenDBHA, bk_cloud_id=0, immute_domain="test.db", bk_biz_id=1
        )
        mock_create_ticket.return_value = MagicMock(id=1)

        partition_objects = {1: [{"db": "test", "table": "test_table"}]}
        result = PartitionHandler.execute_partition("admin", 1, partition_objects)
        assert len(result) == 1
        assert mock_create_ticket.called

    @patch("backend.db_services.partition.handlers.Cluster.objects.get")
    @patch("backend.db_services.partition.handlers.ClusterHandler.get_exact_handler")
    @patch("backend.db_services.partition.handlers.DRSApi.rpc")
    def test_verify_partition_field_success(self, mock_rpc, mock_handler, mock_cluster):
        """测试验证分区字段 - 成功"""
        from backend.db_services.partition.constants import QUERY_DATABASE_FIELD_TYPE, QUERY_UNIQUE_FIELDS_SQL

        mock_cluster.return_value = MagicMock(id=1, bk_cloud_id=0)
        mock_handler.return_value.get_remote_address.return_value = "127.0.0.1:3306"

        # 构造SQL
        table_sts = "(table_name = 'test_table')"
        db_sts = "(table_schema like 'test_db')"
        unique_fields_sql = QUERY_UNIQUE_FIELDS_SQL.format(table_sts=table_sts, db_sts=db_sts)
        fields_type_sql = QUERY_DATABASE_FIELD_TYPE.format(table_sts=table_sts, db_sts=db_sts)

        # 模拟DRS返回
        mock_rpc.return_value = [
            {
                "cmd_results": [
                    {
                        "cmd": unique_fields_sql,
                        "table_data": [
                            {
                                "table_schema": "test_db",
                                "table_name": "test_table",
                                "index_name": "PRIMARY",
                                "column_list": "id,name",
                            }
                        ],
                    },
                    {
                        "cmd": fields_type_sql,
                        "table_data": [
                            {
                                "table_schema": "test_db",
                                "table_name": "test_table",
                                "column_name": "id",
                                "column_type": "int(11)",
                            }
                        ],
                    },
                ]
            }
        ]

        # 不应该抛出异常
        PartitionHandler.verify_partition_field(
            bk_biz_id=1,
            cluster_id=1,
            dblikes=["test_db"],
            tblikes=["test_table"],
            partition_column="id",
            partition_column_type="int",
        )

    @patch("backend.db_services.partition.handlers.Cluster.objects.get")
    @patch("backend.db_services.partition.handlers.ClusterHandler.get_exact_handler")
    @patch("backend.db_services.partition.handlers.DRSApi.rpc")
    def test_verify_partition_field_no_match(self, mock_rpc, mock_handler, mock_cluster):
        """测试验证分区字段 - 无匹配表"""
        from backend.db_services.partition.constants import QUERY_DATABASE_FIELD_TYPE, QUERY_UNIQUE_FIELDS_SQL

        mock_cluster.return_value = MagicMock(id=1, bk_cloud_id=0)
        mock_handler.return_value.get_remote_address.return_value = "127.0.0.1:3306"

        # 构造SQL
        table_sts = "(table_name = 'table%')"
        db_sts = "(table_schema like 'test%')"
        unique_fields_sql = QUERY_UNIQUE_FIELDS_SQL.format(table_sts=table_sts, db_sts=db_sts)
        fields_type_sql = QUERY_DATABASE_FIELD_TYPE.format(table_sts=table_sts, db_sts=db_sts)

        # 返回空的字段类型数据
        mock_rpc.return_value = [
            {"cmd_results": [{"cmd": unique_fields_sql, "table_data": []}, {"cmd": fields_type_sql, "table_data": []}]}
        ]

        with pytest.raises(DBPartitionInvalidFieldException):
            PartitionHandler.verify_partition_field(
                bk_biz_id=1,
                cluster_id=1,
                dblikes=["test%"],
                tblikes=["table%"],
                partition_column="id",
                partition_column_type="int",
            )

    @patch("backend.db_services.partition.handlers.Cluster.objects.get")
    @patch("backend.db_services.partition.handlers.ClusterHandler.get_exact_handler")
    @patch("backend.db_services.partition.handlers.DRSApi.rpc")
    def test_verify_partition_field_invalid_index(self, mock_rpc, mock_handler, mock_cluster):
        """测试验证分区字段 - 不满足索引要求"""
        from backend.db_services.partition.constants import QUERY_DATABASE_FIELD_TYPE, QUERY_UNIQUE_FIELDS_SQL

        mock_cluster.return_value = MagicMock(id=1, bk_cloud_id=0)
        mock_handler.return_value.get_remote_address.return_value = "127.0.0.1:3306"

        # 构造SQL
        table_sts = "(table_name = 'test_table')"
        db_sts = "(table_schema like 'test_db')"
        unique_fields_sql = QUERY_UNIQUE_FIELDS_SQL.format(table_sts=table_sts, db_sts=db_sts)
        fields_type_sql = QUERY_DATABASE_FIELD_TYPE.format(table_sts=table_sts, db_sts=db_sts)

        # 主键不包含分区字段
        mock_rpc.return_value = [
            {
                "cmd_results": [
                    {
                        "cmd": unique_fields_sql,
                        "table_data": [
                            {
                                "table_schema": "test_db",
                                "table_name": "test_table",
                                "index_name": "PRIMARY",
                                "column_list": "name",
                            }
                        ],
                    },
                    {
                        "cmd": fields_type_sql,
                        "table_data": [
                            {
                                "table_schema": "test_db",
                                "table_name": "test_table",
                                "column_name": "id",
                                "column_type": "int(11)",
                            }
                        ],
                    },
                ]
            }
        ]

        with pytest.raises(DBPartitionInvalidFieldException):
            PartitionHandler.verify_partition_field(
                bk_biz_id=1,
                cluster_id=1,
                dblikes=["test_db"],
                tblikes=["test_table"],
                partition_column="id",
                partition_column_type="int",
            )
