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
from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.db_report.enums.kafka_disk_growth_sub_type import (
    KafkaDiskGrowthAiStatus,
    KafkaDiskGrowthRule,
    KafkaDiskGrowthRunKind,
)
from backend.db_report.report_basemodel import BaseReportABS


class KafkaDiskGrowthReport(BaseReportABS):
    """
    Kafka 磁盘持续增长巡检报告
    只记录命中规则的 broker 挂载点，未命中的不写入
    """

    domain = models.CharField(max_length=255, default="", verbose_name=_("集群域名"))
    app = models.CharField(max_length=100, verbose_name=_("业务名"))
    dba = models.JSONField(verbose_name=_("业务所属dba"))
    cluster_type = models.CharField(max_length=64, default="", help_text=_("集群类型"))

    ip = models.CharField(max_length=64, default="", verbose_name=_("Broker IP"))
    mount_point = models.CharField(max_length=255, default="", verbose_name=_("挂载点"))
    check_day = models.DateField(verbose_name=_("判定日期"), help_text=_("早间巡检判定昨天，午后巡检判定今天"))
    run_kind = models.CharField(max_length=16, choices=KafkaDiskGrowthRunKind.get_choices(), default="")
    rule = models.CharField(max_length=32, choices=KafkaDiskGrowthRule.get_choices(), default="")

    peaks = models.JSONField(default=list, verbose_name=_("最近8天日峰值"))
    peak = models.FloatField(default=0, verbose_name=_("判定当天峰值"))
    excess = models.FloatField(default=0, verbose_name=_("比此前7天最高值高出的点数"))
    daily_growth = models.FloatField(default=0, verbose_name=_("近3天日均涨幅"))
    retention_hours = models.IntegerField(null=True, blank=True, verbose_name=_("集群级保留期(小时)"))

    ai_status = models.CharField(
        max_length=16,
        choices=KafkaDiskGrowthAiStatus.get_choices(),
        default=KafkaDiskGrowthAiStatus.NOT_SUBMITTED.value,
        verbose_name=_("AI分析状态"),
    )
    ai_analysis = models.TextField(default="", blank=True, verbose_name=_("AI分析结论"))

    class Meta:
        # 同一挂载点、同一判定日、同一时段只有一行；并发重跑时由数据库兜底，update_or_create 才不会产生重复行
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "ip", "mount_point", "check_day", "run_kind"], name="kdg_report_unique_slot"
            )
        ]
