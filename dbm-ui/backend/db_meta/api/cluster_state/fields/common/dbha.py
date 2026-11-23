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
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Any, Dict, List

from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster_state.fields.base import NativeStateField
from backend.db_meta.api.cluster_state.values import StateValue
from backend.db_meta.enums import StateValueType
from backend.db_meta.exceptions import ClusterStateException
from backend.db_meta.models import Cluster, ClusterDBHAExt

# 不传截止时间时视为永久屏蔽 DBHA，与 Redis 集群下线时的永久屏蔽保持一致
DBHA_DISABLED_FOREVER = datetime(9999, 12, 31, 23, 59, 59, tzinfo=dt_timezone.utc)


@dataclass
class DBHADisabledDetail:
    """DBHA 屏蔽记录"""

    begin_time: datetime
    end_time: datetime
    creator: str


class DBHADisabledField(NativeStateField):
    """
    DBHA 开关，数据来源：ClusterDBHAExt，判断规则与 Cluster.is_dbha_disabled 一致（屏蔽截止时间未过期）。
    写入委托给 Cluster.disable_dbha / enable_dbha，DBHA 拉取实例时的排除逻辑不变
    """

    key = "dbha_disabled"
    name = _("DBHA 禁用")
    help_text = _("集群是否屏蔽了 DBHA 切换，取自 ClusterDBHAExt")
    value_type = StateValueType.BOOL.value
    default_value = False
    filterable = True
    writable = True

    @classmethod
    def disabled_records(cls) -> QuerySet:
        """屏蔽未过期的记录；过期记录由 DBHA 拉取实例的接口定期清理，这里按 end_time 判断"""
        return ClusterDBHAExt.objects.filter(end_time__gte=timezone.now())

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        """一次查询读取整页集群的屏蔽记录，detail 为屏蔽起止时间"""
        records = self.disabled_records().filter(cluster_id__in=cluster_ids)
        details = {
            record.cluster_id: DBHADisabledDetail(
                begin_time=record.begin_time, end_time=record.end_time, creator=record.creator
            )
            for record in records
        }
        return {
            cluster_id: self.make_state(cluster_id in details, detail=details.get(cluster_id))
            for cluster_id in cluster_ids
        }

    def filter_q(self, op: str, values: List[Any]) -> Q:
        """只支持 IN；同时过滤 true 和 false 等于不过滤"""
        disabled = Q(id__in=self.disabled_records().values("cluster_id"))
        if set(values) == {True, False}:
            return Q()
        return disabled if values[0] else ~disabled

    def mark(self, cluster: Cluster, value: Any, extra: Any = None, operator: str = "") -> None:
        """
        value 为 True 时屏蔽 DBHA，extra 可传 {"end_time": 屏蔽截止时间（datetime 或可解析的字符串）}，
        不传为永久屏蔽；value 为 False 时解除屏蔽
        """
        if not self.normalize_value(value):
            self.unmark(cluster, operator)
            return
        end_time = (extra or {}).get("end_time") or DBHA_DISABLED_FOREVER
        if isinstance(end_time, str):
            end_time = parse_datetime(end_time)
        if end_time is None:
            raise ClusterStateException(message=_("状态字段 {} 的屏蔽截止时间不合法").format(self.key))
        cluster.disable_dbha(username=operator, end_time=end_time)

    def unmark(self, cluster: Cluster, operator: str = "") -> None:
        """解除 DBHA 屏蔽"""
        cluster.enable_dbha()
