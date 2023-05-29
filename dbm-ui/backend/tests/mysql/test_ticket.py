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
import pytest

from backend.ticket.views import TicketViewSet
from backend.utils.pytest import AuthorizedAPIRequestFactory, force_authenticate

pytestmark = pytest.mark.django_db

factory = AuthorizedAPIRequestFactory()

CREATE_RECEIPT_PARAMS = {
    "zone": "beijing",
    "network": "IDC",
    "spec": "SA2.MEDIUM8",
    "bk_biz_id": "2005000002",
    "db_module": "2",
    "architecture": "MASTER_SLAVE",
    "disaster_tolerance": "CROSS",
    "version": "MySQL5.7",
    "charset": "UTF-8",
    "proxy_port": 10001,
    "mysql_port": 20001,
    "quantity": 2,
    "domains": [
        {
            "service": "LOLgamedb1",
            "master_domain": "gamedb.data1.lol.db#2000",
            "slave_domain": "gamedr.data1.lol.db#2000",
            "managers": ["admin", "chris"],
        },
        {
            "service": "LOLgamedb2",
            "master_domain": "gamedb.data2.lol.db#2000",
            "slave_domain": "gamedr.data2.lol.db#2000",
            "managers": ["merry"],
        },
    ],
    "remark": "这是一条备注",
}


@pytest.mark.skip()
class TestZoneViewSet:
    # @pytest.mark.skip()
    def test_create_receipt(self):
        request = factory.post("/apis/mysql/ticket/receipts/", data=CREATE_RECEIPT_PARAMS, format="json")
        ticket_viewset = TicketViewSet.as_view({"post": "create"})
        response = ticket_viewset(request)
        assert response.status_code == 200
        data = response.data
        assert "id" in data

    def test_list_receipts(self, bk_user):
        request = factory.get("/apis/mysql/ticket/receipts/")
        force_authenticate(request, user=bk_user)
        ticket_viewset = TicketViewSet.as_view({"get": "list"})
        response = ticket_viewset(request)
        data = response.data
        assert len(data) == 2

    def test_get_receipt(self, bk_user):
        request = factory.get("/apis/mysql/ticket/receipts/1/")
        force_authenticate(request, user=bk_user)
        zone_viewset = TicketViewSet.as_view({"get": "retrieve"})
        response = zone_viewset(request, pk=1)
        data = response.data
        assert data["zone"] == "nanjing"
