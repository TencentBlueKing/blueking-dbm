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
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Any, Dict, List, Optional, Set

from django.db.models import Max, Q, QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster_state.fields.base import NativeStateField, StoredStateField
from backend.db_meta.api.cluster_state.values import StateDetail, StateValue
from backend.db_meta.enums import ClusterPhase, ClusterStatus, DrillDownType, StateValueType
from backend.db_meta.exceptions import ClusterStateException
from backend.db_meta.models import Cluster, ClusterDBHAExt

# 不传截止时间时视为永久屏蔽 DBHA，与 Redis 集群下线时的永久屏蔽保持一致
DBHA_DISABLED_FOREVER = datetime(9999, 12, 31, 23, 59, 59, tzinfo=dt_timezone.utc)


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


# ---------------------------------------------------------------------------
# 平台可选字段：不在 CommonClusterStateSchema 中，组件 Schema 按需引入
# ---------------------------------------------------------------------------


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


@dataclass
class CapacityExtra:
    """容量明细，used / total 单位为字节，in_use 为保留两位小数的使用率百分比"""

    used: float
    total: float
    in_use: float


class CapacityField(StoredStateField):
    """
    集群容量使用率，取值为四舍五入后的整数百分比，没有采集到时为空（没有默认值）。
    由容量采集任务 sync_cluster_stat_by_cluster_type 调用 sync_cluster_capacity_state 批量写入，
    每次采集覆盖同业务同类型的全部集群
    """

    key = "capacity"
    name = _("容量使用率")
    help_text = _("集群容量使用率（%），由容量采集任务定期写入")
    value_type = StateValueType.NUMBER.value
    filterable = True
    extra_class = CapacityExtra

    def get_display(self, value: Any) -> str:
        """展示为百分比"""
        return "" if value is None else f"{value}%"


@dataclass
class PortraitReportDetail:
    """最新一份画像报告的摘要"""

    report_id: int
    score: int
    report_to_time: datetime


class PortraitReportField(NativeStateField):
    """
    集群健康报告，取值为最新一份画像报告的分享链接，没有报告时为空；数据来源：db_report.ClusterPortraitReport。
    报告表在 report_db，不能与 Cluster 联表，按 (业务, 域名) 分两次查询
    """

    key = "portrait_report"
    name = _("健康报告")
    help_text = _("集群最新一份画像报告的链接，取自 ClusterPortraitReport")
    value_type = StateValueType.STR.value
    drilldown_type = DrillDownType.LINK.value

    def get_display(self, value: Any) -> str:
        """有报告时展示固定文案，链接放在 value 里由前端跳转"""
        return str(_("查看报告")) if value else ""

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        """
        先在报告库按 (业务, 域名) 取最大 id 的已完成报告，再取其内容。
        报告表只追加写入，最大 id 即最新一份报告；域名可能被重建的集群复用，早于集群创建时间的报告不算
        """
        from backend.db_report.models.cluster_portrait_report import ClusterPortraitReport

        clusters = Cluster.objects.filter(id__in=cluster_ids).values("id", "bk_biz_id", "immute_domain", "create_at")
        clusters = {(cluster["bk_biz_id"], cluster["immute_domain"]): cluster for cluster in clusters}
        completed = ClusterPortraitReport.objects.filter(
            bk_biz_id__in={bk_biz_id for bk_biz_id, _domain in clusters},
            cluster_domain__in={domain for _bk_biz_id, domain in clusters},
        ).exclude(share_url="")
        latest_ids = completed.values("bk_biz_id", "cluster_domain").annotate(latest_id=Max("id"))
        reports = ClusterPortraitReport.objects.filter(id__in=[item["latest_id"] for item in latest_ids])

        states: Dict[int, StateValue] = {}
        for report in reports:
            cluster = clusters.get((report.bk_biz_id, report.cluster_domain))
            if cluster is None or report.report_to_time < cluster["create_at"]:
                continue
            detail = PortraitReportDetail(
                report_id=report.id, score=report.score, report_to_time=report.report_to_time
            )
            states[cluster["id"]] = self.make_state(report.share_url, detail=detail)
        return {cluster_id: states.get(cluster_id) or self.make_state(None) for cluster_id in cluster_ids}

    def get_detail(self, cluster: Cluster, state: StateValue) -> Optional[StateDetail]:
        """前端打开 url 跳转到报告页"""
        if not state.value:
            return None
        return StateDetail.kv(
            columns=[("url", _("报告链接")), ("score", _("健康分")), ("report_to_time", _("报告时间"))],
            data={"url": state.value, "score": state.detail.score, "report_to_time": state.detail.report_to_time},
        )
