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
import random
from unittest.mock import patch

import pytest

from backend.configuration.constants import DEFAULT_CLUSTER_STATE_DISPLAY_FIELDS, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_services.cluster_state import views
from backend.tests.db_meta.api.cluster_state.base import create_cluster
from backend.ticket.constants import FlowType, TicketStatus, TicketType
from backend.ticket.models import ClusterOperateRecord, Flow, Ticket
from backend.utils.pytest import AuthorizedAPIRequestFactory

pytestmark = pytest.mark.django_db

factory = AuthorizedAPIRequestFactory()


def call(action: str, url_path: str, bk_biz_id: int, query: str):
    request = factory.get(f"/apis/cluster_state/bizs/{bk_biz_id}/{url_path}/{query}")
    view = views.ClusterStateViewSet.as_view({"get": action})
    return view(request, bk_biz_id=bk_biz_id)


@pytest.fixture
def bk_biz_id():
    return random.randint(300000, 400000)


UNREGISTERED_CLUSTER_TYPE = ClusterType.TendisPredixyRedisCluster.value


@pytest.fixture
def display_config():
    SystemSettings.objects.update_or_create(
        key=SystemSettingsEnum.CLUSTER_STATE_DISPLAY_FIELDS.value,
        defaults={
            "type": "dict",
            "value": {"tendbsingle": ["phase", "status", "running_ticket"], UNREGISTERED_CLUSTER_TYPE: ["phase"]},
        },
    )


@patch.object(views.ClusterStateViewSet, "get_permissions", lambda x: [])
class TestClusterStateViews:
    def test_schema(self, bk_biz_id, display_config):
        data = call("get_state_schema", "schema", bk_biz_id, "?cluster_type=tendbsingle").data
        assert [f["key"] for f in data["fields"]] == ["phase", "status", "running_ticket"]
        assert data["display_fields"] == ["phase", "status", "running_ticket"]
        running_ticket = data["fields"][2]
        assert (running_ticket["value_type"], running_ticket["drilldown_type"], running_ticket["filterable"]) == (
            "multi",
            "TICKET_LIST",
            True,
        )
        assert {c["value"]: c["label"] for c in data["fields"][0]["choices"]}["offline"] == "禁用"

    def test_schema_without_display_config(self, bk_biz_id):
        SystemSettings.objects.filter(key=SystemSettingsEnum.CLUSTER_STATE_DISPLAY_FIELDS.value).delete()
        data = call("get_state_schema", "schema", bk_biz_id, "?cluster_type=tendbsingle").data
        assert data["display_fields"] == DEFAULT_CLUSTER_STATE_DISPLAY_FIELDS["tendbsingle"]

    def test_schema_unregistered_cluster_type(self, bk_biz_id, display_config):
        data = call("get_state_schema", "schema", bk_biz_id, f"?cluster_type={UNREGISTERED_CLUSTER_TYPE}").data
        # 配置了但集群类型未声明该字段时，下发前过滤掉
        assert data == {"cluster_type": UNREGISTERED_CLUSTER_TYPE, "fields": [], "display_fields": []}

    def test_schema_display_fallback_per_cluster_type(self, bk_biz_id, display_config):
        # 线上配置里没有 tendbha 时取该类型的默认值，不需要先改配置
        data = call("get_state_schema", "schema", bk_biz_id, "?cluster_type=tendbha").data
        assert data["display_fields"] == DEFAULT_CLUSTER_STATE_DISPLAY_FIELDS["tendbha"]
        fields = {f["key"]: f for f in data["fields"]}
        assert (fields["capacity"]["source"], fields["capacity"]["value_type"]) == ("stored", "number")
        assert (fields["dbha_disabled"]["writable"], fields["portrait_report"]["drilldown_type"]) == (True, "LINK")

    def test_detail(self, bk_biz_id):
        cluster = create_cluster(ClusterType.TenDBSingle.value, bk_biz_id)
        ticket = Ticket.objects.create(
            bk_biz_id=bk_biz_id, ticket_type=TicketType.MYSQL_SINGLE_APPLY, status=TicketStatus.RUNNING
        )
        flow = Flow.objects.create(ticket=ticket, flow_type=FlowType.INNER_FLOW)
        ClusterOperateRecord.objects.create(cluster_id=cluster.id, ticket=ticket, flow=flow)

        data = call("get_state_detail", "detail", bk_biz_id, f"?cluster_id={cluster.id}&key=running_ticket").data
        assert data["type"] == "table"
        assert data["data"][0]["ticket_id"] == ticket.id

    def test_detail_cross_biz(self, bk_biz_id):
        cluster = create_cluster(ClusterType.TenDBSingle.value, bk_biz_id)
        response = call("get_state_detail", "detail", bk_biz_id + 1, f"?cluster_id={cluster.id}&key=running_ticket")
        assert json.loads(response.content)["result"] is False
