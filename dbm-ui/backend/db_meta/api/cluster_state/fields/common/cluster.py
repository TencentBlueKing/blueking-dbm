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
from typing import Any, Dict, List

from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster_state.fields.base import NativeStateField
from backend.db_meta.api.cluster_state.values import StateValue
from backend.db_meta.enums import ClusterPhase, ClusterStatus, StateValueType
from backend.db_meta.models import Cluster


class PhaseField(NativeStateField):
    """集群阶段，数据来源：Cluster.phase"""

    key = "phase"
    name = _("集群阶段")
    help_text = _("集群的启用/禁用阶段，取自 Cluster.phase")
    value_type = StateValueType.ENUM.value
    filterable = True
    choices = ClusterPhase.get_choices()

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        """一次查询读取整页集群的 phase"""
        phases = Cluster.objects.filter(id__in=cluster_ids).values_list("id", "phase")
        return {cluster_id: self.make_state(phase) for cluster_id, phase in phases}

    def filter_q(self, op: str, values: List[Any]) -> Q:
        """只支持 IN"""
        return Q(phase__in=values)


class StatusField(NativeStateField):
    """集群健康状态，数据来源：Cluster.status"""

    key = "status"
    name = _("集群状态")
    help_text = _("集群的健康状态，取自 Cluster.status")
    value_type = StateValueType.ENUM.value
    filterable = True
    choices = ClusterStatus.get_choices()

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        """一次查询读取整页集群的 status"""
        statuses = Cluster.objects.filter(id__in=cluster_ids).values_list("id", "status")
        return {cluster_id: self.make_state(status) for cluster_id, status in statuses}

    def filter_q(self, op: str, values: List[Any]) -> Q:
        """只支持 IN"""
        return Q(status__in=values)
