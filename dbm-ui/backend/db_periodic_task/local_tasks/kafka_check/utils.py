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
import logging
from datetime import datetime

from django.utils import timezone

from backend.db_report.enums import ReportStateType
from backend.db_report.models import KafkaBrokerAffinityReport, KafkaZookeeperAffinityReport

logger = logging.getLogger("celery")


def calculate_kafka_broker_failed_days(cluster, log_end_time: datetime = None) -> int:
    """
    计算Kafka Broker亲和性检查的连续失败天数：
    - 找最近一个正常（ReportStateType.NORMAL）的报告（按 id 倒序），如果找不到则取最早的一条报告（按 id 升序）
    - 以 log_end_time - report.create_at 的天数差返回
    - 如果没有任何报告则返回 1（首次失败）
    """
    if log_end_time is None:
        log_end_time = timezone.now()

    report = (
        KafkaBrokerAffinityReport.objects.filter(
            bk_biz_id=cluster.bk_biz_id, domain=cluster.immute_domain, state=ReportStateType.NORMAL.value
        )
        .order_by("-id")
        .first()
    )
    if not report:
        report = (
            KafkaBrokerAffinityReport.objects.filter(bk_biz_id=cluster.bk_biz_id, domain=cluster.immute_domain)
            .order_by("id")
            .first()
        )
    if not report:
        return 1
    # 确保天数差至少为 1
    delta_days = max(1, (log_end_time - report.create_at).days)
    return delta_days


def calculate_kafka_zookeeper_failed_days(cluster, log_end_time: datetime = None) -> int:
    """
    计算Kafka Zookeeper亲和性检查的连续失败天数：
    - 找最近一个正常（ReportStateType.NORMAL）的报告（按 id 倒序），如果找不到则取最早的一条报告（按 id 升序）
    - 以 log_end_time - report.create_at 的天数差返回
    - 如果没有任何报告则返回 1（首次失败）
    """
    if log_end_time is None:
        log_end_time = timezone.now()

    report = (
        KafkaZookeeperAffinityReport.objects.filter(
            bk_biz_id=cluster.bk_biz_id, domain=cluster.immute_domain, state=ReportStateType.NORMAL.value
        )
        .order_by("-id")
        .first()
    )
    if not report:
        report = (
            KafkaZookeeperAffinityReport.objects.filter(bk_biz_id=cluster.bk_biz_id, domain=cluster.immute_domain)
            .order_by("id")
            .first()
        )
    if not report:
        return 1
    # 确保天数差至少为 1
    delta_days = max(1, (log_end_time - report.create_at).days)
    return delta_days
