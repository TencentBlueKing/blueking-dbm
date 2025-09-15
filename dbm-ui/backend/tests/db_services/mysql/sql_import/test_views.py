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
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.configuration.constants import DBType
from backend.db_services.mysql.sql_import.views import SQLImportViewSet
from backend.tests.mock_data import constant
from backend.tests.mock_data.components.sql_import import SQLSimulationApiMock
from backend.tests.mock_data.components.storage import get_storage_mock
from backend.tests.mock_data.iam_app.permission import PermissionMock

pytestmark = pytest.mark.django_db
client = APIClient()
client.login(username="admin")


@pytest.fixture(autouse=True)
def set_empty_middleware():
    """禁用中间件以简化测试"""
    with patch.object(settings, "MIDDLEWARE", []):
        yield


@pytest.fixture(autouse=True)
def setup_permissions():
    """设置权限 - 禁用权限验证"""
    patch.object(SQLImportViewSet, "permission_classes", [AllowAny]).start()
    patch.object(SQLImportViewSet, "get_permissions", lambda x: []).start()
    patch("backend.iam_app.handlers.permission.Permission", PermissionMock).start()
    yield


class TestSQLImportViewSet:
    """测试 SQLImportViewSet 类 - SQL导入相关视图"""

    @patch("backend.db_services.mysql.sql_import.handlers.get_storage", get_storage_mock)
    @patch("backend.db_services.mysql.sql_import.handlers.SQLSimulationApi", SQLSimulationApiMock)
    @patch("backend.db_services.mysql.sql_import.handlers.BizSettings.get_setting_value")
    def test_grammar_check_with_content(self, mock_get_setting):
        """测试SQL语法检查 - 传入SQL内容"""
        mock_get_setting.return_value = False

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/grammar_check/"
        data = {
            "cluster_type": DBType.MySQL.value,
            "sql_content": "SELECT * FROM user WHERE id = 1;",
            "versions": ["MySQL-5.7"],
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert isinstance(result, dict)
        assert len(result) > 0

    @patch("backend.db_services.mysql.sql_import.handlers.get_storage", get_storage_mock)
    @patch("backend.db_services.mysql.sql_import.handlers.SQLSimulationApi", SQLSimulationApiMock)
    @patch("backend.db_services.mysql.sql_import.handlers.BizSettings.get_setting_value")
    def test_grammar_check_with_execute_objects(self, mock_get_setting):
        """测试SQL语法检查 - 包含执行对象"""
        import json

        mock_get_setting.return_value = False

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/grammar_check/"
        # execute_objects 需要是JSON字符串格式
        execute_objects_str = json.dumps(
            [
                {
                    "dbnames": ["test_db"],
                    "ignore_dbnames": [],
                    "sql_files": [],
                }
            ]
        )
        data = {
            "cluster_type": DBType.MySQL.value,
            "sql_content": "INSERT INTO user (name) VALUES ('test');",
            "versions": ["MySQL-5.7"],
            "execute_objects": execute_objects_str,
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert isinstance(result, dict)

    @patch("backend.db_services.mysql.sql_import.handlers.get_storage", get_storage_mock)
    @patch("backend.db_services.mysql.sql_import.handlers.MySQLController")
    @patch("backend.db_services.mysql.sql_import.handlers.generate_root_id")
    @patch("backend.utils.redis.RedisConn.zadd")
    @patch("backend.utils.redis.RedisConn.set")
    @patch("backend.utils.redis.RedisConn.zrangebyscore")
    @patch("backend.utils.cache.data_cache")
    def test_semantic_check_mysql(
        self, mock_data_cache, mock_zrangebyscore, mock_set, mock_zadd, mock_gen_root_id, mock_controller
    ):
        """测试SQL语义检查 - MySQL集群"""
        mock_gen_root_id.return_value = "test_root_123"
        mock_zrangebyscore.return_value = []
        mock_controller_instance = MagicMock()
        mock_controller.return_value = mock_controller_instance

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/semantic_check/"
        data = {
            "cluster_type": DBType.MySQL.value,
            "charset": "utf8mb4",
            "cluster_ids": [1],
            "execute_objects": [
                {
                    "dbnames": ["test_db"],
                    "sql_files": ["test.sql"],
                    "import_mode": "file",  # 添加必需的import_mode字段
                }
            ],
            "ticket_type": "MYSQL_IMPORT_SQLFILE",
            "ticket_mode": {"mode": "manual"},
            "backup": [],
            "is_auto_commit": False,
            "remark": "test semantic check",
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "root_id" in result
        assert result["root_id"] == "test_root_123"
        assert mock_controller_instance.mysql_sql_semantic_check_scene.called

    @patch("backend.db_services.mysql.sql_import.handlers.get_storage", get_storage_mock)
    @patch("backend.db_services.mysql.sql_import.handlers.SpiderController")
    @patch("backend.db_services.mysql.sql_import.handlers.generate_root_id")
    @patch("backend.utils.redis.RedisConn.zadd")
    @patch("backend.utils.redis.RedisConn.set")
    @patch("backend.utils.redis.RedisConn.zrangebyscore")
    @patch("backend.utils.cache.data_cache")
    def test_semantic_check_tendbcluster(
        self, mock_data_cache, mock_zrangebyscore, mock_set, mock_zadd, mock_gen_root_id, mock_controller
    ):
        """测试SQL语义检查 - TenDBCluster集群"""
        mock_gen_root_id.return_value = "spider_root_456"
        mock_zrangebyscore.return_value = []
        mock_controller_instance = MagicMock()
        mock_controller.return_value = mock_controller_instance

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/semantic_check/"
        data = {
            "cluster_type": DBType.TenDBCluster.value,
            "charset": "utf8mb4",
            "cluster_ids": [2],
            "execute_objects": [
                {
                    "dbnames": ["spider_db"],
                    "sql_files": ["spider.sql"],
                    "import_mode": "file",  # 添加必需的import_mode字段
                }
            ],
            "ticket_type": "TENDBCLUSTER_IMPORT_SQLFILE",
            "ticket_mode": {"mode": "auto"},
            "backup": [],
            "is_auto_commit": True,
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "root_id" in result
        assert mock_controller_instance.spider_semantic_check_scene.called

    @patch("backend.utils.redis.RedisConn.zrange")
    @patch("backend.utils.redis.RedisConn.mget")
    @patch("backend.flow.models.FlowTree.objects.filter")
    def test_get_user_semantic_tasks(self, mock_filter, mock_mget, mock_zrange):
        """测试获取用户语义检查任务列表"""
        # Mock Redis返回的任务ID
        mock_zrange.return_value = ["root_1", "root_2"]
        mock_mget.return_value = ["RUNNING", "FINISHED"]

        # Mock FlowTree查询
        tree1 = MagicMock()
        tree1.root_id = "root_1"
        tree1.bk_biz_id = constant.BK_BIZ_ID
        tree1.status = "RUNNING"
        tree1.created_at = "2024-01-01 00:00:00"

        tree2 = MagicMock()
        tree2.root_id = "root_2"
        tree2.bk_biz_id = constant.BK_BIZ_ID
        tree2.status = "FINISHED"
        tree2.created_at = "2024-01-01 00:01:00"

        mock_filter.return_value = [tree1, tree2]

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/get_user_semantic_tasks/?cluster_type={DBType.MySQL.value}"
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert isinstance(result, list)
        assert len(result) >= 0

    @patch("backend.utils.redis.RedisConn.zrem")
    @patch("backend.utils.redis.RedisConn.delete")
    def test_delete_user_semantic_tasks(self, mock_delete, mock_zrem):
        """测试删除用户语义检查任务列表"""
        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/delete_user_semantic_tasks/"
        data = {"cluster_type": DBType.MySQL.value, "task_ids": ["root_to_delete_1", "root_to_delete_2"]}
        response = client.delete(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert mock_zrem.called
        assert mock_delete.called

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.revoke_pipeline")
    def test_revoke_semantic_check(self, mock_revoke):
        """测试终止语义检查流程"""
        mock_result = MagicMock()
        mock_result.result = True
        mock_result.message = "Successfully revoked"
        mock_result.data = {}
        mock_revoke.return_value = mock_result

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/revoke_semantic_check/"
        data = {"cluster_type": DBType.MySQL.value, "root_id": "root_to_revoke"}
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert result["result"] is True
        assert "message" in result
        assert mock_revoke.called

    @patch("backend.flow.models.FlowNode.objects.filter")
    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_node_input_data")
    def test_query_semantic_data_from_engine(self, mock_get_input, mock_filter):
        """测试查询语义执行数据 - 从引擎获取"""
        # Mock FlowNode
        first_node = MagicMock()
        first_node.node_id = "node_123"
        mock_filter.return_value.first.return_value = first_node

        # Mock BambooEngine返回数据
        mock_input_data = MagicMock()
        mock_input_data.data = {
            "global_data": {
                "cluster_ids": [1],
                "execute_objects": [{"dbnames": ["db1"], "sql_files": ["test.sql", "test2.sql"]}],
                "charset": "utf8mb4",
            }
        }
        mock_get_input.return_value = mock_input_data

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/query_semantic_data/"
        data = {"cluster_type": DBType.MySQL.value, "root_id": "query_root_id"}
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "execute_sql_files" in result
        assert "cluster_ids" in result

    @patch("backend.flow.models.FlowNode.objects.filter")
    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_node_input_data")
    @patch("backend.utils.cache.cache.get")
    def test_query_semantic_data_from_cache(self, mock_cache_get, mock_get_input, mock_filter):
        """测试查询语义执行数据 - 从缓存获取"""
        # Mock FlowNode
        first_node = MagicMock()
        first_node.node_id = "node_456"
        mock_filter.return_value.first.return_value = first_node

        # Mock BambooEngine抛出KeyError，走缓存逻辑
        mock_get_input.side_effect = KeyError("global_data not found")

        # Mock cache返回数据
        mock_cache_get.return_value = {
            "cluster_ids": [2],
            "execute_objects": [{"dbnames": ["cached_db"], "sql_files": ["cached.sql"]}],
        }

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/query_semantic_data/"
        data = {"cluster_type": DBType.MySQL.value, "root_id": "cache_root_id"}
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert "execute_sql_files" in result

    @patch("backend.db_services.mysql.sql_import.handlers.TaskFlowHandler")
    @patch("backend.db_services.mysql.sql_import.handlers.SQLHandler.query_semantic_data")
    def test_get_semantic_check_result_logs(self, mock_query_semantic_data, mock_taskflow_handler):
        """测试获取语义执行结果日志"""
        # Mock query_semantic_data
        mock_query_semantic_data.return_value = {"semantic_data": {"execute_sql_files": ["test.sql"]}}

        # Mock TaskFlowHandler
        mock_handler_instance = MagicMock()
        mock_handler_instance.get_node_histories.return_value = [{"version": "v1"}]
        mock_handler_instance.get_version_logs.return_value = [
            {"message": "[start]-test.sql", "timestamp": "2024-01-01 00:00:00"},
            {"message": "Query OK, 1 row affected", "timestamp": "2024-01-01 00:00:01"},
            {"message": "[end]-test.sql", "timestamp": "2024-01-01 00:00:02"},
        ]
        mock_taskflow_handler.return_value = mock_handler_instance

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/get_semantic_check_result_logs/"
        data = {
            "cluster_type": DBType.MySQL.value,
            "root_id": "log_root_id",
            "node_id": "semantic_node",
            "sql_files": ["test.sql"],
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert isinstance(result, list)

    @patch("backend.db_services.mysql.sql_import.handlers.FlowTree.objects.get")
    @patch("backend.db_services.mysql.sql_import.handlers.FlowNode.objects.get")
    @patch("backend.db_services.mysql.sql_import.handlers.TaskFlowHandler")
    @patch("backend.db_services.mysql.sql_import.handlers.SQLSimulationApi.query_semantic_result")
    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_node_input_data")
    def test_get_semantic_execute_result(
        self, mock_get_input, mock_query_result, mock_taskflow_handler, mock_flownode_get, mock_flowtree_get
    ):
        """测试获取语义执行结果"""
        # Mock FlowTree
        mock_tree = MagicMock()
        mock_tree.tree = {"nodes": []}
        mock_flowtree_get.return_value = mock_tree

        # Mock TaskFlowHandler
        mock_handler_instance = MagicMock()
        mock_handler_instance.get_node_id_by_component.return_value = ["semantic_node"]
        mock_taskflow_handler.return_value = mock_handler_instance

        # Mock FlowNode
        mock_node = MagicMock()
        mock_node.version_id = "version_123"
        mock_flownode_get.return_value = mock_node

        # Mock SQLSimulationApi
        mock_query_result.return_value = [{"line_id": 0, "result": "success"}]

        # Mock BambooEngine
        mock_input_data = MagicMock()
        mock_input_data.data = {
            "global_data": {"execute_objects": [{"line_id": 0, "dbnames": ["test_db"], "ignore_dbnames": []}]}
        }
        mock_get_input.return_value = mock_input_data

        url = f"/apis/mysql/bizs/{constant.BK_BIZ_ID}/sql_import/get_semantic_execute_result/"
        data = {
            "cluster_type": DBType.MySQL.value,
            "root_id": "result_root_id",
        }
        response = client.post(url, data=data, content_type="application/json")

        assert response.status_code == status.HTTP_200_OK
        result = response.json()["data"]
        assert isinstance(result, list)
