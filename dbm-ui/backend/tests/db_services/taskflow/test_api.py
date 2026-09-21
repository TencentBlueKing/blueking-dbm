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

import json
import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.db_services.taskflow.views.flow import TaskFlowViewSet
from backend.flow.models import FlowNode, FlowTree, StateType
from backend.tests.mock_data import constant
from backend.tests.mock_data.db_services import taskflow
from backend.ticket.constants import TicketType

logger = logging.getLogger("test")
client = APIClient()
pytestmark = pytest.mark.django_db


@pytest.fixture
def init_taskflow():
    FlowTree.objects.create(
        uid=425,
        tree=taskflow.TREE_DATA,
        bk_biz_id=constant.BK_BIZ_ID,
        ticket_type=TicketType.MYSQL_SEMANTIC_CHECK.value,
        root_id=taskflow.ROOT_ID,
        status=StateType.FINISHED.value,
    )
    FlowNode.objects.create(
        uid=425,
        root_id=taskflow.ROOT_ID,
        node_id=taskflow.NODE_ID,
        status=StateType.FINISHED.value,
        version_id=taskflow.VERSION_ID,
    )


class TestTaskflowApi:
    """
    测试taskflow相关api
    """

    # 注意: 测试类不能定义__init__，否则pytest不会收集该类下的用例
    @pytest.fixture(autouse=True)
    def disable_middleware(self, settings):
        settings.MIDDLEWARE = []

    root_id = taskflow.ROOT_ID
    node_id = taskflow.NODE_ID
    version_id = taskflow.VERSION_ID

    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_taskflow_retrieve(self, mocked_permission_classes, init_taskflow):
        mocked_permission_classes.return_value = [AllowAny]

        url = f"/apis/taskflow/{self.root_id}/"
        data = client.get(url).data
        assert data["flow_info"]["root_id"] == self.root_id

    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_histories(self, mocked_permission_classes, init_taskflow):
        mocked_permission_classes.return_value = [AllowAny]

        url = f"/apis/taskflow/{self.root_id}/node_histories/"
        data = client.get(url, data={"node_id": self.node_id}).data

        assert len(data) == 1
        assert data[0]["version"] == self.version_id

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log(self, mocked_permission_classes, mock_esquery, mock_get_histories, init_taskflow):
        mocked_permission_classes.return_value = [AllowAny]
        # 构造当前版本的历史，保证日志未过保留期
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]

        hits = [
            self.generate_log_hit(now, gse_index=1, iteration_index=1, message="first log"),
            self.generate_log_hit(now, gse_index=1, iteration_index=2, message="second log"),
        ]

        def esquery_side_effect(**kwargs):
            # node_log 是一次性全量预览：不排序、不翻页，两个采集源各查一次
            assert kwargs.get("sort_list") is None
            assert kwargs.get("search_after") is None
            if "dbm_log" not in kwargs["indices"]:
                return []
            return hits

        mock_esquery.side_effect = esquery_side_effect

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        data = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id}).data

        assert isinstance(data, list)
        assert len(data) == 2
        assert "first log" in data[0]["message"]
        assert "second log" in data[1]["message"]

    @patch("backend.db_services.taskflow.handlers._node_log_lines", return_value=(1, 1))
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    def test_node_log_too_large(self, mock_esquery, mock_get_histories, mock_log_lines, init_taskflow):
        """日志行数超过 node_log_v2 的前后缀阈值时，返回省略行并标记 too_large。"""
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]
        head_hits = [
            self.generate_log_hit(now, gse_index=1, iteration_index=i, message=f"head-{i}") for i in range(1, 5)
        ]
        tail_hit = self.generate_log_hit(now, gse_index=1, iteration_index=5, message="tail")

        def esquery_side_effect(**kwargs):
            if "dbm_log" not in kwargs["indices"]:
                return []
            # 正序探测取前 limit 条，倒序补最新的 limit 条
            assert kwargs["sort_list"][0][0] == "dtEventTimeStamp"
            hits = head_hits if kwargs["sort_list"][0][1] == "asc" else [tail_hit]
            return hits[: kwargs["limit"]]

        mock_esquery.side_effect = esquery_side_effect

        log_data = TaskFlowHandler(root_id=self.root_id).get_version_logs_v2(self.node_id, self.version_id)
        mock_log_lines.assert_called_once()
        assert log_data["too_large"] is True
        messages = "".join(item["message"] for item in log_data["logs"])
        assert "日志过大" in messages
        assert "head-1" in messages
        assert "tail" in messages

    @patch("backend.db_services.taskflow.handlers._node_log_lines", return_value=(1, 1))
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    def test_node_log_v2_incremental_returns_full_batch(
        self, mock_esquery, mock_get_histories, mock_log_lines, init_taskflow
    ):
        """带 cursor 的增量拉取直接返回该批日志，不做首尾取样/省略，也不额外发倒序查询。"""
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]
        cursor = [int(now.timestamp() * 1000), 1, 0]
        # 增量批次超过阈值(2)，按首屏逻辑会走 前缀 + 省略行 + 倒序后缀
        hits = [self.generate_log_hit(now, gse_index=1, iteration_index=i, message=f"new-{i}") for i in range(1, 5)]

        def esquery_side_effect(**kwargs):
            if "dbm_log" not in kwargs["indices"]:
                return []
            assert kwargs["sort_list"][0][1] == "asc"
            assert kwargs.get("search_after") == cursor
            return hits[: kwargs["limit"]]

        mock_esquery.side_effect = esquery_side_effect

        log_data = TaskFlowHandler(root_id=self.root_id).get_version_logs_v2(
            self.node_id, self.version_id, cursor=cursor
        )

        assert log_data["too_large"] is False
        messages = [item["message"] for item in log_data["logs"]]
        assert len(messages) == 3  # threshold + 1 = 3，单窗口内全量返回
        assert all("new-" in message for message in messages)
        assert not any("日志过大" in message for message in messages)
        # 只有两个源各一次正序查询，没有倒序 tail 查询
        assert mock_esquery.call_count == 2

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log_without_data(self, mocked_permission_classes, mock_esquery, mock_get_histories, init_taskflow):
        """无日志时返回占位提示。"""
        mocked_permission_classes.return_value = [AllowAny]
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]
        mock_esquery.return_value = []

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        data = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id}).data
        assert isinstance(data, list)
        assert len(data) == 1
        assert "日志上报中" in data[0]["message"]

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log_download(self, mocked_permission_classes, mock_esquery, mock_get_histories, init_taskflow):
        """下载返回文本附件，两个采集源按时间正序合并后一次性写出。"""
        mocked_permission_classes.return_value = [AllowAny]
        now = timezone.now()
        earlier = now - timedelta(seconds=2)
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]
        first_hit = self.generate_log_hit(now, gse_index=2, iteration_index=1, message="flow-new")
        second_hit = self.generate_log_hit(now, gse_index=2, iteration_index=2, message="flow-newer")
        actuator_hit = self.generate_log_hit(earlier, gse_index=1, iteration_index=1, message="actuator-old")

        def esquery_side_effect(**kwargs):
            # 下载与预览共用一次性全量拉取，不分页、不排序
            assert kwargs["offset"] == 0
            assert kwargs["limit"] == 10000
            assert kwargs.get("sort_list") is None
            assert kwargs.get("search_after") is None
            return [first_hit, second_hit] if "dbm_log" in kwargs["indices"] else [actuator_hit]

        mock_esquery.side_effect = esquery_side_effect

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        response = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id, "download": True})

        assert response.status_code == 200
        assert response["Content-Type"] == "application/text charset=utf-8"
        assert response["Content-Disposition"] == (
            f'attachment; filename="{self.root_id}-{self.node_id}-{self.version_id}.log"'
        )
        text = response.content.decode("utf-8")
        # 两个采集源按时间正序归并
        assert text.index("actuator-old") < text.index("flow-new") < text.index("flow-newer")
        assert mock_esquery.call_count == 2

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log_download_unknown_version(
        self, mocked_permission_classes, mock_esquery, mock_get_histories, init_taskflow
    ):
        """版本不存在时不查询 bklog，下载响应里给出占位提示而不是空文件。"""
        mocked_permission_classes.return_value = [AllowAny]
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": "other-version", "started_time": now - timedelta(hours=1), "finished_time": now}
        ]

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        response = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id, "download": True})

        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/text")
        assert "无法找到当前版本" in response.content.decode("utf-8")
        mock_esquery.assert_not_called()

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log_download_interrupted_returns_error(
        self, mocked_permission_classes, mock_esquery, mock_get_histories, settings, init_taskflow
    ):
        """采集中途失败时由全局异常处理返回带原因的 JSON，不产出半成品下载文件。"""
        # DEBUG=True 时自定义 handler 会放行异常，这里固定走返回 JsonResponse 的分支
        settings.DEBUG = False
        mocked_permission_classes.return_value = [AllowAny]
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]
        first_hit = self.generate_log_hit(now, gse_index=1, iteration_index=1, message="first log")

        def esquery_side_effect(**kwargs):
            # 第一个采集源正常，第二个采集源失败
            if "dbm_log" in kwargs["indices"]:
                return [first_hit]
            raise Exception("bklog timeout")

        mock_esquery.side_effect = esquery_side_effect

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        response = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id, "download": True})

        assert "Content-Disposition" not in response
        body = json.loads(response.content)
        assert body["result"] is False
        assert "bklog timeout" in body["message"]

    @staticmethod
    def generate_log_hit(timestamp, gse_index: int, iteration_index: int, message: str) -> dict:
        """构造一条bklog日志命中记录"""
        return {
            "_source": {
                "log": json.dumps({"levelname": "INFO", "msg": message}),
                "serverIp": "127.0.0.1",
                "dtEventTimeStamp": int(timestamp.timestamp() * 1000),
                "gseIndex": gse_index,
                "iterationIndex": iteration_index,
            },
            "_index": "test_index",
            "sort": [int(timestamp.timestamp() * 1000), gse_index, iteration_index],
        }
