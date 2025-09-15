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
from datetime import timedelta
from unittest.mock import patch

import pytest
from bamboo_engine.api import EngineAPIResult
from django.utils import timezone

from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.flow.consts import StateType
from backend.flow.models import FlowNode, FlowNodeOperateRecord, FlowTree
from backend.tests.mock_data import constant
from backend.tests.mock_data.db_services import taskflow
from backend.ticket.constants import TicketType

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_flow_tree():
    """创建测试流程树"""
    tree = FlowTree.objects.create(
        uid=425,
        tree=taskflow.TREE_DATA,
        bk_biz_id=constant.BK_BIZ_ID,
        ticket_type=TicketType.MYSQL_SEMANTIC_CHECK.value,
        root_id=taskflow.ROOT_ID,
        status=StateType.RUNNING.value,
    )
    yield tree
    tree.delete()


@pytest.fixture
def test_flow_node():
    """创建测试流程节点"""
    node = FlowNode.objects.create(
        uid=425,
        root_id=taskflow.ROOT_ID,
        node_id=taskflow.NODE_ID,
        status=StateType.RUNNING.value,
        version_id=taskflow.VERSION_ID,
    )
    yield node
    node.delete()


@pytest.fixture
def test_failed_flow_node():
    """创建失败的测试流程节点"""
    node = FlowNode.objects.create(
        uid=426,
        root_id=taskflow.ROOT_ID,
        node_id="failed_node_id",
        status=StateType.FAILED.value,
        version_id=taskflow.VERSION_ID,
    )
    yield node
    node.delete()


class TestTaskFlowHandler:
    """测试 TaskFlowHandler 类"""

    def test_init(self):
        """测试初始化"""
        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        assert handler.root_id == taskflow.ROOT_ID

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.revoke_pipeline")
    def test_revoke_pipeline_success(self, mock_revoke, test_flow_tree):
        """测试撤销流程 - 成功"""
        mock_revoke.return_value = EngineAPIResult(result=True, message="撤销成功")

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        result = handler.revoke_pipeline(operator="admin", remark="测试撤销")

        assert result.result
        # 验证操作记录被创建
        assert FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).exists()
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    def test_revoke_pipeline_already_revoked(self, test_flow_tree):
        """测试撤销流程 - 已撤销"""
        test_flow_tree.status = StateType.REVOKED
        test_flow_tree.save()

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        result = handler.revoke_pipeline(operator="admin")

        assert result.result
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    def test_revoke_pipeline_pending(self):
        """测试撤销流程 - 待创建状态"""
        tree = FlowTree.objects.create(
            uid=999,
            tree=taskflow.TREE_DATA,
            bk_biz_id=constant.BK_BIZ_ID,
            ticket_type=TicketType.MYSQL_SEMANTIC_CHECK.value,
            root_id="pending_root_id",
            status=StateType.CREATED.value,
        )

        handler = TaskFlowHandler(root_id="pending_root_id")
        result = handler.revoke_pipeline(operator="admin")

        assert result.result
        tree.refresh_from_db()
        assert tree.status == StateType.REVOKED
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id="pending_root_id").delete()
        tree.delete()

    @patch("backend.db_services.taskflow.task.retry_node")
    def test_retry_node(self, mock_retry, test_flow_node):
        """测试重试节点"""
        mock_retry.return_value = EngineAPIResult(result=True, message="重试成功")

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        result = handler.retry_node(node_id=taskflow.NODE_ID, operator="admin")

        assert result.result
        assert mock_retry.called
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.skip_node")
    def test_skip_node(self, mock_skip, test_flow_node):
        """测试跳过节点"""
        mock_skip.return_value = EngineAPIResult(result=True, message="跳过成功")

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        result = handler.skip_node(node_id=taskflow.NODE_ID, operator="admin")

        assert result.result
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.force_fail_node")
    def test_force_fail_node(self, mock_force_fail, test_flow_node):
        """测试强制失败节点"""
        mock_force_fail.return_value = EngineAPIResult(result=True, message="强制失败成功")

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        result = handler.force_fail_node(node_id=taskflow.NODE_ID, operator="admin")

        assert result.result
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_pipeline_tree_states")
    def test_get_specific_node_ids(self, mock_get_states, test_flow_node):
        """测试获取特定状态的节点ID列表"""
        mock_get_states.return_value = {
            "activities": {
                "node1": {"type": "ServiceActivity", "status": StateType.FAILED},
                "node2": {"type": "ServiceActivity", "status": StateType.RUNNING},
                "node3": {"type": "ServiceActivity", "status": StateType.FAILED},
            }
        }

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        failed_nodes = handler.get_specific_node_ids(status=StateType.FAILED)

        assert len(failed_nodes) == 2
        assert "node1" in failed_nodes
        assert "node3" in failed_nodes

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_pipeline_tree_states")
    def test_get_specific_node_ids_with_subpipeline(self, mock_get_states):
        """测试获取特定状态的节点ID列表 - 包含子流程"""
        mock_get_states.return_value = {
            "activities": {
                "parent_node": {
                    "type": "SubProcess",
                    "status": StateType.RUNNING,
                    "pipeline": {
                        "activities": {
                            "child_node1": {"type": "ServiceActivity", "status": StateType.FAILED},
                            "child_node2": {"type": "ServiceActivity", "status": StateType.RUNNING},
                        }
                    },
                }
            }
        }

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        failed_nodes = handler.get_specific_node_ids(status=StateType.FAILED)

        assert len(failed_nodes) == 1
        assert "child_node1" in failed_nodes

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_node_short_histories")
    def test_get_node_histories(self, mock_get_histories, test_flow_node):
        """测试获取节点历史版本"""
        now = timezone.now()
        # 为test_flow_node设置时间
        test_flow_node.started_at = now - timedelta(minutes=30)
        test_flow_node.updated_at = now
        test_flow_node.save()

        mock_get_histories.return_value = [
            {
                "started_time": now - timedelta(hours=2),
                "archived_time": now - timedelta(hours=1),
                "version": "v1",
            }
        ]

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        histories = handler.get_node_histories(node_id=taskflow.NODE_ID)

        assert len(histories) == 2
        # 应该按时间倒序排列
        assert histories[0]["version"] == taskflow.VERSION_ID

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_node_execution_data")
    def test_get_node_execution_data(self, mock_get_data, test_flow_node):
        """测试获取节点执行数据"""
        mock_data = {"inputs": {"param1": "value1"}, "outputs": {"result": "success"}}
        mock_get_data.return_value = EngineAPIResult(result=True, message="success", data=mock_data)

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        result = handler.get_node_execution_data(node_id=taskflow.NODE_ID)

        assert result == mock_data

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_pipeline_tree")
    def test_get_node_operate_records(self, mock_get_tree, test_flow_node):
        """测试获取节点操作记录"""
        mock_get_tree.return_value = {
            "activities": {
                taskflow.NODE_ID: {"name": "测试节点", "type": "ServiceActivity"},
            }
        }

        # 创建操作记录
        FlowNodeOperateRecord.objects.create(
            root_id=taskflow.ROOT_ID,
            node_id=taskflow.NODE_ID,
            operator="admin",
            operate_type="retry",
        )

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        records = handler.get_node_operate_records(node_id=taskflow.NODE_ID)

        assert len(records) == 1
        assert records[0]["node_name"] == "测试节点"
        assert records[0]["operator"] == "admin"
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    def test_get_node_id_by_component(self):
        """测试根据组件获取节点ID"""
        tree = {
            "activities": {
                "node1": {"component": {"code": "test_component"}},
                "node2": {"component": {"code": "other_component"}},
                "node3": {
                    "pipeline": {
                        "activities": {
                            "subnode1": {"component": {"code": "test_component"}},
                        }
                    }
                },
            }
        }

        node_ids = TaskFlowHandler.get_node_id_by_component(tree, "test_component")

        assert len(node_ids) == 2
        assert "node1" in node_ids
        assert "subnode1" in node_ids

    @patch("backend.components.BKLogApi.esquery_search")
    def test_bklog_esquery_search(self, mock_esquery):
        """测试BKLog ES查询"""
        mock_esquery.return_value = {"hits": {"hits": [{"_source": {"log": "test log"}}]}}

        result = TaskFlowHandler.bklog_esquery_search(
            indices="test_index",
            query_string="test query",
            start_time="2023-01-01 00:00:00",
            end_time="2023-01-01 23:59:59",
        )

        assert len(result) == 1
        assert result[0]["_source"]["log"] == "test log"

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    def test_get_version_logs(self, mock_get_histories, mock_esquery, test_flow_node):
        """测试获取节点版本日志"""
        now = timezone.now()
        mock_get_histories.return_value = [
            {
                "started_time": now - timedelta(hours=1),
                "finished_time": now,
                "version": taskflow.VERSION_ID,
            }
        ]
        mock_esquery.side_effect = [
            # dbm_log查询结果
            [
                {
                    "_source": {
                        "log": '{"levelname": "INFO", "msg": "Test log message"}',
                        "serverIp": "127.0.0.1",
                        "time": "2023-01-01 12:00:00",
                        "dtEventTimeStamp": "1672574400000",
                        "gseIndex": "1",
                        "iterationIndex": "1",
                    },
                    "_index": "test_index",
                }
            ],
            # dbactuator查询结果
            [],
        ]

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        logs = handler.get_version_logs(node_id=taskflow.NODE_ID, version_id=taskflow.VERSION_ID)

        assert len(logs) >= 1
        assert "message" in logs[0]

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    def test_get_version_logs_node_not_run(self, mock_get_histories):
        """测试获取节点版本日志 - 节点未运行"""
        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        logs = handler.get_version_logs(node_id="non_existent_node", version_id="v1")

        assert len(logs) == 1
        assert "节点尚未运行" in logs[0]["message"]

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    def test_get_version_logs_version_not_found(self, mock_get_histories, test_flow_node):
        """测试获取节点版本日志 - 版本不存在"""
        mock_get_histories.return_value = [
            {
                "version": taskflow.VERSION_ID,
                "started_time": timezone.now(),
                "finished_time": timezone.now(),
            }
        ]

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        logs = handler.get_version_logs(node_id=taskflow.NODE_ID, version_id="non_existent_version")

        assert len(logs) == 1
        assert "无法找到当前版本" in logs[0]["message"]

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    def test_get_version_error_logs(self, mock_get_histories, mock_esquery, test_flow_node):
        """测试获取节点错误日志"""
        now = timezone.now()
        mock_get_histories.return_value = [
            {
                "started_time": now - timedelta(hours=1),
                "finished_time": now,
                "version": taskflow.VERSION_ID,
            }
        ]
        mock_esquery.return_value = [
            {
                "_source": {
                    "log": '{"levelname": "ERROR", "msg": "Error message"}',
                    "serverIp": "127.0.0.1",
                    "time": "2023-01-01 12:00:00",
                    "dtEventTimeStamp": "1672574400000",
                    "gseIndex": "1",
                    "iterationIndex": "1",
                },
                "_index": "test_dbactuator",
            }
        ]

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        logs = handler.get_version_error_logs(node_id=taskflow.NODE_ID, version_id=taskflow.VERSION_ID)

        assert len(logs) >= 1

    def test_generate_log_record(self):
        """测试生成日志记录"""
        log_record = TaskFlowHandler.generate_log_record(message="test message", levelname="INFO")

        assert log_record["message"] == "test message"
        assert log_record["levelname"] == "INFO"
        assert "timestamp" in log_record

    def test_format_log_flow_log(self):
        """测试格式化日志 - flow日志"""
        log_str = '{"levelname": "INFO", "msg": "Test message"}'
        # 使用实际的index格式
        result = TaskFlowHandler._format_log(log_str, "127.0.0.1", "2005000002_bklog_dbm_log")

        assert result is not None
        assert result["levelname"] == "INFO"
        # INFO级别的日志不添加前缀
        assert "Test message" in result["log"]

    def test_format_log_dbactuator_log(self):
        """测试格式化日志 - dbactuator日志"""
        log_str = '{"levelname": "ERROR", "msg": "Error occurred"}'
        result = TaskFlowHandler._format_log(log_str, "127.0.0.1", "test_dbactuator")

        assert result is not None
        assert result["levelname"] == "ERROR"
        assert "[dbactuator-127.0.0.1]" in result["log"]
        assert "##[error]" in result["log"]

    def test_format_log_debug_level(self):
        """测试格式化日志 - DEBUG级别（应该被过滤）"""
        log_str = '{"levelname": "DEBUG", "msg": "Debug message"}'
        result = TaskFlowHandler._format_log(log_str, "127.0.0.1", "test_index")

        assert result is None

    def test_format_log_invalid_json(self):
        """测试格式化日志 - 无效JSON"""
        log_str = "invalid json string"
        result = TaskFlowHandler._format_log(log_str, "127.0.0.1", "test_index")

        assert result is None

    @patch("backend.db_services.taskflow.task.retry_node")
    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_pipeline_tree_states")
    def test_batch_retry_nodes(self, mock_get_states, mock_retry, test_failed_flow_node):
        """测试批量重试节点"""
        mock_get_states.return_value = {
            "activities": {
                "failed_node_id": {"type": "ServiceActivity", "status": StateType.FAILED},
            }
        }
        mock_retry.return_value = EngineAPIResult(result=True, message="success")

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        handler.batch_retry_nodes(operator="admin")

        assert mock_retry.called
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.force_fail_node")
    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_pipeline_tree_states")
    def test_batch_force_fail_nodes(self, mock_get_states, mock_force_fail, test_flow_node):
        """测试批量强制失败节点"""
        mock_get_states.return_value = {
            "activities": {
                taskflow.NODE_ID: {"type": "ServiceActivity", "status": StateType.RUNNING},
            }
        }
        mock_force_fail.return_value = EngineAPIResult(result=True, message="success")

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        handler.batch_force_fail_nodes(operator="admin")

        assert mock_force_fail.called
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.skip_node")
    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_pipeline_tree_states")
    def test_batch_skip_nodes(self, mock_get_states, mock_skip, test_failed_flow_node):
        """测试批量跳过节点"""
        mock_get_states.return_value = {
            "activities": {
                "failed_node_id": {"type": "ServiceActivity", "status": StateType.FAILED},
            }
        }
        mock_skip.return_value = EngineAPIResult(result=True, message="success")

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        handler.batch_skip_nodes(operator="admin")

        assert mock_skip.called
        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()

    @patch("backend.flow.engine.bamboo.engine.BambooEngine.callback")
    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_pipeline_tree_states")
    def test_callback_node(self, mock_get_states, mock_callback, test_flow_node):
        """测试回调节点"""
        mock_callback.return_value = EngineAPIResult(result=True, message="success")
        mock_get_states.return_value = {"activities": {}}

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)
        result = handler.callback_node(node_id=taskflow.NODE_ID, desc={"status": "success"})

        assert result.result
        assert mock_callback.called

    @patch("backend.db_services.taskflow.task.retry_node")
    @patch("backend.flow.engine.bamboo.engine.BambooEngine.get_pipeline_tree_states")
    def test_batch_operate_nodes_partial_success(self, mock_get_states, mock_retry):
        """测试批量操作节点 - 部分成功"""
        # 创建两个失败节点
        node1 = FlowNode.objects.create(
            uid=500,
            root_id=taskflow.ROOT_ID,
            node_id="fail_node_1",
            status=StateType.FAILED.value,
            version_id="v1",
        )
        node2 = FlowNode.objects.create(
            uid=501,
            root_id=taskflow.ROOT_ID,
            node_id="fail_node_2",
            status=StateType.FAILED.value,
            version_id="v1",
        )

        mock_get_states.return_value = {
            "activities": {
                "fail_node_1": {"type": "ServiceActivity", "status": StateType.FAILED},
                "fail_node_2": {"type": "ServiceActivity", "status": StateType.FAILED},
            }
        }
        # 第一个成功，第二个失败
        mock_retry.side_effect = [EngineAPIResult(result=True, message="success"), Exception("重试失败")]

        handler = TaskFlowHandler(root_id=taskflow.ROOT_ID)

        with pytest.raises(Exception):
            handler.batch_retry_nodes(operator="admin")

        # 清理
        FlowNodeOperateRecord.objects.filter(root_id=taskflow.ROOT_ID).delete()
        node1.delete()
        node2.delete()
