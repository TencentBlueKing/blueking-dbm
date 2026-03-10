"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.db_report.enums import ReportStateType
from backend.db_report.report_basemodel import BaseReportABS


class RedisCheckReport(BaseReportABS):
    """RedisCheckReport 用于记录Redis的检查结果. 用sub_type区分检查子项
    目前只有redis_exporter的up指标检查子项
    """

    cluster_id = models.IntegerField(default=0, verbose_name=_("集群 id"))
    cluster = models.CharField(max_length=255, default="")
    cluster_type = models.CharField(max_length=128, verbose_name=_("集群类型"), default="")
    shard = models.CharField(max_length=100, verbose_name=_("shard or set_name"), default="")
    instance = models.CharField(max_length=100, verbose_name=_("实例节点 ip:port"))
    subtype = models.CharField(max_length=100, verbose_name=_("检查子项"))
    report_day = models.IntegerField(default=0, verbose_name=_("报告日期"))

    class Meta:
        indexes = [
            models.Index(fields=["bk_biz_id", "create_at"]),
            models.Index(fields=["status", "create_at"]),
            models.Index(fields=["creator", "create_at"]),
            models.Index(fields=["cluster", "create_at"]),
            models.Index(fields=["subtype", "report_day", "cluster_id"]),
            models.Index(fields=["subtype", "create_at", "cluster_id"]),
            models.Index(fields=["subtype", "bk_biz_id", "state", "create_at"]),
        ]

    @classmethod
    def upsert_by_cluster_subtype(
        cls,
        *,
        cluster_id: int,
        subtype: str,
        cluster: str,
        cluster_type: str,
        bk_biz_id: int,
        bk_cloud_id: int,
        report_day: int,
        creator: str,
        state: str,
        msg: str,
        shard: str = "",
        instance: str = "",
    ) -> "RedisCheckReport":
        """Create or update a record by (cluster_id, subtype). Returns the saved instance.
        When multiple rows match, updates only the latest one (by create_at).
        Only updates if that record was modified within the last 36 hours; otherwise creates new.
        """
        UPSERT_WINDOW = timedelta(hours=36)
        now = timezone.now()
        cutoff = now - UPSERT_WINDOW
        defaults = {
            "report_day": report_day,
            "cluster": cluster,
            "cluster_type": cluster_type,
            "bk_biz_id": bk_biz_id,
            "bk_cloud_id": bk_cloud_id,
            "shard": shard,
            "instance": instance,
            "state": state,
            "msg": msg,
            "creator": creator,
            "updater": creator,
            "failed_days": 0 if state == "normal" else 1,
            "update_at": now,
            "create_at": now,
        }
        existing = (
            cls.objects.filter(
                cluster_id=cluster_id,
                subtype=subtype,
                create_at__gte=cutoff,
            )
            .order_by("-create_at")
            .first()
        )
        if existing:
            old_failed_days = existing.failed_days
            old_state = existing.state
            for key, value in defaults.items():
                setattr(existing, key, value)
            if state != ReportStateType.NORMAL.value:
                existing.failed_days = old_failed_days + 1 if old_state != ReportStateType.NORMAL.value else 1
            else:
                existing.failed_days = 0
            existing.save(update_fields=list(defaults.keys()))
            return existing
        return cls.objects.create(
            cluster_id=cluster_id,
            subtype=subtype,
            **defaults,
        )
