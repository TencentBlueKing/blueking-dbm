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
from unittest.mock import patch

import pytest

from backend.db_services.mysql.resources.tendbsingle import views
from backend.tests.mock_data.components.cc import CCApiMock
from backend.ticket.constants import FlowType, TicketStatus, TicketType
from backend.ticket.models import ClusterOperateRecord, Flow, Ticket
from backend.utils.pytest import AuthorizedAPIRequestFactory

pytestmark = pytest.mark.django_db

factory = AuthorizedAPIRequestFactory()


def list_dbsingle(bk_biz_id: int, query: str = ""):
    request = factory.get(f"/apis/mysql/bizs/{bk_biz_id}/tendbsingle_resources/{query}")
    view = views.DBSingleViewSet.as_view({"get": "list"})
    return view(request, bk_biz_id=bk_biz_id)


@pytest.fixture
def running_ticket(dbsingle_cluster):
    ticket = Ticket.objects.create(
        bk_biz_id=dbsingle_cluster.bk_biz_id, ticket_type=TicketType.MYSQL_SINGLE_APPLY, status=TicketStatus.RUNNING
    )
    flow = Flow.objects.create(ticket=ticket, flow_type=FlowType.INNER_FLOW)
    ClusterOperateRecord.objects.create(cluster_id=dbsingle_cluster.id, ticket=ticket, flow=flow)
    return ticket


@patch("backend.db_services.ipchooser.query.resource.CCApi", CCApiMock())
@patch.object(views.DBSingleViewSet, "get_permissions", lambda x: [])
class TestDBSingleClusterState:
    def test_list_without_states(self, dbsingle_cluster, bk_biz_id, running_ticket):
        """列表暂不挂载 states，避免每页额外查库；原有字段不受影响"""
        response = list_dbsingle(bk_biz_id)
        assert "states" not in response.data["results"][0]
        assert response.data["results"][0]["operations"][0]["ticket_id"] == running_ticket.id

    def test_list_filter_by_state(self, dbsingle_cluster, bk_biz_id, running_ticket):
        assert list_dbsingle(bk_biz_id, f"?state__running_ticket={running_ticket.id}").data["count"] == 1
        assert list_dbsingle(bk_biz_id, f"?state__running_ticket={running_ticket.id + 1}").data["count"] == 0
        assert list_dbsingle(bk_biz_id, "?state__phase=offline").data["count"] == 0
        assert list_dbsingle(bk_biz_id, "?state__phase=online&state__status=normal").data["count"] == 1

    def test_list_invalid_state_filter(self, dbsingle_cluster, bk_biz_id):
        response = list_dbsingle(bk_biz_id, "?state__not_declared=1")
        assert json.loads(response.content)["result"] is False
