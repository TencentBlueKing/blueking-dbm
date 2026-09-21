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
            # dbm_log采集日志按offset/limit分页返回，dbactuator采集日志此处不关注
            if "dbm_log" in kwargs["indices"]:
                return hits[kwargs["offset"] : kwargs["offset"] + kwargs["limit"]]
            return []

        mock_esquery.side_effect = esquery_side_effect

        url = f"/apis/taskflow/{self.root_id}/node_log/"
        data = client.get(
            url, data={"node_id": self.node_id, "version_id": self.version_id, "offset": 0, "limit": 1}
        ).data

        assert set(data.keys()) == {"has_data", "next", "previous", "results"}
        assert data["has_data"] is True
        assert len(data["results"]) == 1
        # 有数据时返回下一页链接，无上一页
        assert data["next"] is not None and "offset=1" in data["next"]
        assert data["previous"] is None

        # offset超出总数时，results为空，不再返回next，而是返回回退上一页的previous
        data = client.get(
            url, data={"node_id": self.node_id, "version_id": self.version_id, "offset": 100, "limit": 1}
        ).data
        assert data["results"] == []
        assert data["has_data"] is False
        assert data["next"] is None
        assert data["previous"] is not None and "offset=99" in data["previous"]

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
        }
