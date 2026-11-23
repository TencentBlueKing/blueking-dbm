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
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster_state.fields.base import NativeStateField
from backend.db_meta.api.cluster_state.values import StateDetail, StateValue
from backend.db_meta.enums import DrillDownType, StateValueType
from backend.db_meta.exceptions import ClusterStateException
from backend.db_meta.models import Cluster


class RunningTicketField(NativeStateField):
    """集群关联的运行中单据，取值为单据 ID 列表；数据来源：ClusterOperateRecord 关联的状态为运行中的单据"""

    key = "running_ticket"
    name = _("关联单据")
    help_text = _("集群当前运行中的单据ID列表，取自集群操作记录 ClusterOperateRecord")
    value_type = StateValueType.MULTI.value
    default_value = []
    filterable = True
    drilldown_type = DrillDownType.TICKET_LIST.value

    @classmethod
    def running_records(cls) -> QuerySet:
        """运行中单据的集群操作记录，ticket 依赖 db_meta，延迟 import"""
        from backend.ticket.constants import TICKET_RUNNING_STATUS_SET
        from backend.ticket.models import ClusterOperateRecord

        return ClusterOperateRecord.objects.filter(ticket__status__in=TICKET_RUNNING_STATUS_SET)

    def normalize_value(self, value: Any) -> int:
        """元素为单据 ID"""
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ClusterStateException(message=_("状态字段 {} 的取值 {} 不合法").format(self.key, value))

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        """一次查询读取整页集群的运行中单据，取值为去重后倒序的单据 ID 列表，没有单据时为空列表"""
        records = self.running_records().filter(cluster_id__in=cluster_ids).values_list("cluster_id", "ticket_id")
        cluster_ticket_ids: Dict[int, Set[int]] = defaultdict(set)
        for cluster_id, ticket_id in records:
            cluster_ticket_ids[cluster_id].add(ticket_id)
        return {
            cluster_id: self.make_state(sorted(cluster_ticket_ids.get(cluster_id, set()), reverse=True))
            for cluster_id in cluster_ids
        }

    def filter_q(self, op: str, values: List[Any]) -> Q:
        """只支持 IN：命中关联了其中任一运行中单据的集群"""
        return Q(id__in=self.running_records().filter(ticket_id__in=values).values("cluster_id"))

    def get_detail(self, cluster: Cluster, state: StateValue) -> Optional[StateDetail]:
        """运行中单据列表，以表格形式返回"""
        records = self.running_records().filter(cluster_id=cluster.id).select_related("ticket").order_by("-ticket_id")
        tickets: Dict[int, Dict[str, Any]] = {}
        for record in records:
            ticket = record.ticket
            tickets.setdefault(
                ticket.id,
                {
                    "ticket_id": ticket.id,
                    "ticket_type": ticket.ticket_type,
                    "ticket_type_display": ticket.get_ticket_type_display(),
                    "status": ticket.status,
                    "status_display": ticket.get_status_display(),
                    "creator": ticket.creator,
                    "create_at": ticket.create_at,
                },
            )
        return StateDetail.table(
            columns=[
                ("ticket_id", _("单据ID")),
                ("ticket_type_display", _("单据类型")),
                ("status_display", _("单据状态")),
                ("creator", _("创建人")),
                ("create_at", _("创建时间")),
            ],
            data=list(tickets.values()),
        )
