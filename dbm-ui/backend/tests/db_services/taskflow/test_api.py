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

import gzip
import json
import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

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
            # 预览按时间正序拉一页；翻页游标非空时视为没有更多
            if "dbm_log" not in kwargs["indices"] or kwargs.get("search_after"):
                return []
            assert kwargs["sort_list"][0] == ["dtEventTimeStamp", "asc"]
            return hits

        mock_esquery.side_effect = esquery_side_effect

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        data = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id}).data

        assert set(data.keys()) == {"result", "too_large"}
        assert data["too_large"] is False
        assert "first log" in data["result"][0]["message"]
        assert "second log" in data["result"][1]["message"]

    @patch("backend.db_services.taskflow.handlers.env.MAX_LOG_SIZE_MB", 0)
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log_too_large(self, mocked_permission_classes, mock_esquery, mock_get_histories, init_taskflow):
        """累计大小超过阈值时停止，并标记 too_large。"""
        mocked_permission_classes.return_value = [AllowAny]
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]
        mock_esquery.return_value = [self.generate_log_hit(now, gse_index=1, iteration_index=1, message="big")]

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        data = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id}).data
        assert data["too_large"] is True
        assert data["result"] == []

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
        assert data["too_large"] is False
        assert "日志上报中" in data["result"][0]["message"]

    @patch("backend.db_services.taskflow.handlers.LOG_DOWNLOAD_PAGE_SIZE", 1)
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log_download_gzip(self, mocked_permission_classes, mock_esquery, mock_get_histories, init_taskflow):
        """下载按页 search_after，响应是 gzip 文件而不是 Content-Encoding。"""
        mocked_permission_classes.return_value = [AllowAny]
        now = timezone.now()
        earlier = now - timedelta(seconds=2)
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]
        first_hit = self.generate_log_hit(now, gse_index=2, iteration_index=1, message="flow-new")
        second_hit = self.generate_log_hit(now, gse_index=2, iteration_index=2, message="flow-newer")
        dbm_pages = {None: [first_hit], tuple(first_hit["sort"]): [second_hit]}
        actuator_hit = self.generate_log_hit(earlier, gse_index=1, iteration_index=1, message="actuator-old")

        def esquery_side_effect(**kwargs):
            cursor = kwargs.get("search_after")
            cursor_key = None if not cursor else tuple(cursor)
            if "dbm_dbactuator" not in kwargs["indices"]:
                assert kwargs["sort_list"][0] == ["dtEventTimeStamp", "asc"]
                assert kwargs["limit"] == 1
                assert kwargs["offset"] == 0
                return dbm_pages.get(cursor_key, [])
            return [] if cursor else [actuator_hit]

        mock_esquery.side_effect = esquery_side_effect

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        response = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id, "download": True})

        assert response.status_code == 200
        assert response["Content-Type"] == "application/gzip"
        assert response["Content-Disposition"] == (
            f'attachment; filename="{self.root_id}-{self.node_id}-{self.version_id}.log.gz"'
        )
        assert response["X-Accel-Buffering"] == "no"
        assert "Content-Encoding" not in response
        text = gzip.decompress(b"".join(response.streaming_content)).decode("utf-8")
        # 两个采集源按时间正序合并，dbm_log 内部按 search_after 翻页
        assert text.index("actuator-old") < text.index("flow-new") < text.index("flow-newer")
        dbm_calls = [call for call in mock_esquery.call_args_list if "dbm_dbactuator" not in call.kwargs["indices"]]
        assert dbm_calls[0].kwargs.get("search_after") in (None, [])
        assert dbm_calls[1].kwargs["search_after"] == first_hit["sort"]

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log_download_rejects_before_stream(
        self, mocked_permission_classes, mock_esquery, mock_get_histories, init_taskflow
    ):
        """版本不存在时返回 400 + JSON（不是文件），不进入 gzip 生成器。"""
        mocked_permission_classes.return_value = [AllowAny]
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": "other-version", "started_time": now - timedelta(hours=1), "finished_time": now}
        ]

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        response = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id, "download": True})

        assert response.status_code == 400
        assert "gzip" not in response["Content-Type"]
        assert "Content-Disposition" not in response
        assert "message" in response.json()
        mock_esquery.assert_not_called()

    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.get_node_histories")
    @patch("backend.db_services.taskflow.handlers.TaskFlowHandler.bklog_esquery_search")
    @patch.object(TaskFlowViewSet, "permission_classes")
    @patch.object(TaskFlowViewSet, "get_permissions", lambda x: [])
    def test_node_log_download_interrupted_still_flushes(
        self, mocked_permission_classes, mock_esquery, mock_get_histories, init_taskflow
    ):
        """中途拉取失败也要写入错误行并 flush，不能给用户一个静默截断、解压才报错的 gzip。"""
        mocked_permission_classes.return_value = [AllowAny]
        now = timezone.now()
        mock_get_histories.return_value = [
            {"version": self.version_id, "started_time": now - timedelta(hours=1), "finished_time": now}
        ]
        first_hit = self.generate_log_hit(now, gse_index=1, iteration_index=1, message="first log")

        def esquery_side_effect(**kwargs):
            # 第一页正常，翻页时报错
            if kwargs.get("search_after"):
                raise Exception("bklog timeout")
            return [first_hit] if "dbm_log" in kwargs["indices"] else []

        mock_esquery.side_effect = esquery_side_effect

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        response = client.get(url, data={"node_id": self.node_id, "version_id": self.version_id, "download": True})

        assert response.status_code == 200
        # 能解压说明 flush 执行了，gzip 结尾合法
        text = gzip.decompress(b"".join(response.streaming_content)).decode("utf-8")
        assert "first log" in text
        assert "日志拉取中断" in text
        assert "bklog timeout" in text

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
