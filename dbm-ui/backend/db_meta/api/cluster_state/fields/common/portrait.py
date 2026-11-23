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
from typing import Any, Dict, List, Optional

from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster_state.fields.base import NativeStateField
from backend.db_meta.api.cluster_state.values import StateDetail, StateValue
from backend.db_meta.enums import DrillDownType, StateValueType
from backend.db_meta.models import Cluster


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
