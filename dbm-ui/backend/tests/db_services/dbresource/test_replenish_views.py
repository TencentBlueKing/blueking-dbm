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
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient

from backend.db_services.dbresource.views.replenish import DBReplenishViewSet
from backend.ticket.constants import TicketStatus

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
    """禁用权限校验，聚焦导出逻辑"""
    with patch.object(DBReplenishViewSet, "permission_classes", [AllowAny]), patch.object(
        DBReplenishViewSet, "get_permissions", return_value=[]
    ):
        yield


class TestDBReplenishViewSet:
    @staticmethod
    def _build_ticket_apply_info(status_value, flow_obj_id, err_msg):
        return {
            "ticket": SimpleNamespace(status=status_value),
            "inner_flow": SimpleNamespace(flow_obj_id=flow_obj_id, err_msg=err_msg),
            "details": {
                "db_type": "mysql",
                "city": "gz",
                "subzone": "sz",
                "os_name": "linux",
                "spec": {"spec_machine_type": "backend", "spec_name": "S5.4XL"},
            },
            "apply_count": 2,
            "delivery_count": 1,
        }

    @patch("backend.db_services.dbresource.views.replenish.ExcelHandler.response")
    @patch("backend.db_services.dbresource.views.replenish.ExcelHandler.serialize")
    @patch("backend.db_services.dbresource.views.replenish.TaskFlowHandler.get_version_logs")
    @patch("backend.db_services.dbresource.views.replenish.TaskFlowHandler.get_specific_nodes")
    @patch("backend.db_services.dbresource.views.replenish.ResourceHandler.get_replenish_ticket_apply_info_map")
    @patch.object(settings, "CONCURRENT_NUMBER", new=2)
    def test_export_replenish_tickets_with_node_logs(
        self, mock_get_apply_info, mock_get_specific_nodes, mock_get_version_logs, mock_serialize, mock_response
    ):
        """失败单据优先使用失败节点日志，成功单据错误日志为空"""
        mock_get_apply_info.return_value = {
            1: self._build_ticket_apply_info(TicketStatus.FAILED, "root-1", "flow-error-fallback"),
            2: self._build_ticket_apply_info(TicketStatus.SUCCEEDED, "root-2", ""),
        }
        mock_get_specific_nodes.return_value = [{"node_id": "node-1", "version_id": "v1"}]
        mock_get_version_logs.return_value = [{"message": "error-1"}, {"message": "error-2"}]
        mock_serialize.side_effect = lambda rows, **kwargs: {"rows": rows}
        mock_response.side_effect = lambda wb, filename: Response({"rows": wb["rows"], "filename": filename})

        response = client.post(
            "/apis/dbresource/replenish/export_replenish_tickets/",
            data={"ticket_ids": [1, 2]},
            content_type="application/json",
        )

        assert response.status_code == status.HTTP_200_OK
        rows = response.json()["data"]["rows"]
        assert len(rows) == 2
        assert rows[0]["ticket_id"] == 1
        assert rows[0]["error_log"] == "error-1\nerror-2"
        assert rows[1]["ticket_id"] == 2
        assert rows[1]["error_log"] == ""
        assert mock_get_specific_nodes.call_count == 1
        assert mock_get_version_logs.call_count == 1
