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
import random

import pytest

from backend.db_meta.api.cluster_state import ClusterStateService
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.exceptions import ValidationError
from backend.tests.db_meta.api.cluster_state.base import StateFieldTestCase, create_cluster
from backend.ticket.constants import FlowType, TicketStatus, TicketType
from backend.ticket.models import ClusterOperateRecord, Flow, Ticket

pytestmark = pytest.mark.django_db


def create_operate_record(cluster_id: int, ticket: Ticket):
    flow = Flow.objects.create(ticket=ticket, flow_type=FlowType.INNER_FLOW)
    ClusterOperateRecord.objects.create(cluster_id=cluster_id, ticket=ticket, flow=flow)


@pytest.fixture
def clusters():
    bk_biz_id = random.randint(200000, 300000)
    return [create_cluster(ClusterType.TenDBSingle.value, bk_biz_id) for _ in range(3)]


@pytest.fixture
def tickets(clusters):
    """集群0：两张运行中单据（其中一张有两个 flow）；集群1：一张已完成单据；集群2：无记录"""
    bk_biz_id = clusters[0].bk_biz_id
    running_1 = Ticket.objects.create(
        bk_biz_id=bk_biz_id, ticket_type=TicketType.MYSQL_SINGLE_APPLY, status=TicketStatus.RUNNING
    )
    running_2 = Ticket.objects.create(
        bk_biz_id=bk_biz_id, ticket_type=TicketType.MYSQL_SINGLE_DESTROY, status=TicketStatus.FAILED
    )
    succeeded = Ticket.objects.create(
        bk_biz_id=bk_biz_id, ticket_type=TicketType.MYSQL_SINGLE_APPLY, status=TicketStatus.SUCCEEDED
    )
    create_operate_record(clusters[0].id, running_1)
    create_operate_record(clusters[0].id, running_1)
    create_operate_record(clusters[0].id, running_2)
    create_operate_record(clusters[1].id, succeeded)
    return [running_1, running_2, succeeded]


class TestTenDBSingleCommonFields(StateFieldTestCase):
    cluster_type = ClusterType.TenDBSingle.value

    def test_running_ticket_value(self, clusters, tickets):
        states = self.get_states(clusters)
        running_ids = sorted([tickets[0].id, tickets[1].id], reverse=True)
        state = states[clusters[0].id]["running_ticket"]
        assert (state.value, state.display) == (running_ids, ",".join(str(i) for i in running_ids))
        assert states[clusters[1].id]["running_ticket"].value == []
        assert states[clusters[2].id]["running_ticket"].value == []

    def test_running_ticket_filter(self, clusters, tickets):
        ids = [cluster.id for cluster in clusters]
        running_1, running_2, succeeded = tickets
        cases = [
            ("state__running_ticket", f"{running_1.id}", {ids[0]}),
            ("state__running_ticket", f"{running_1.id},{running_2.id}", {ids[0]}),
            # 已完成的单据不算运行中
            ("state__running_ticket", f"{succeeded.id}", set()),
        ]
        for param, raw, expected in cases:
            assert self.filter_cluster_ids(param, raw, clusters) == expected, (param, raw)
        for param, raw in [("state__running_ticket__gte", "1"), ("state__running_ticket", "abc")]:
            with pytest.raises(ValidationError):
                self.filter_cluster_ids(param, raw, clusters)

    def test_running_ticket_list_and_detail(self, clusters, tickets):
        cluster_infos = [self.cluster_info(cluster) for cluster in clusters]
        ClusterStateService.fill_states(cluster_infos)
        # 列表只下发取值，不包含下钻内容
        assert "drilldown" not in cluster_infos[0]["states"]["running_ticket"]

        detail = ClusterStateService.get_detail(clusters[0], "running_ticket")
        assert detail.type == "table"
        assert [row["ticket_id"] for row in detail.data] == sorted([tickets[0].id, tickets[1].id], reverse=True)
        assert detail.to_dict()["columns"][0] == {"key": "ticket_id", "name": "单据ID"}

    def test_phase_and_status(self, clusters):
        clusters[1].phase = ClusterPhase.OFFLINE.value
        clusters[1].save(update_fields=["phase"])
        assert self.filter_cluster_ids("state__phase", "offline", clusters) == {clusters[1].id}
        assert self.filter_cluster_ids("state__status", "normal", clusters) == {c.id for c in clusters}

        state = self.get_state(clusters[1], "phase")
        assert (state.value, state.display) == ("offline", "禁用")
