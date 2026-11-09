# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed on the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from celery.schedules import crontab

from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.kafka_check.kafka_broker_check import check_kafka_broker_affinity
from backend.db_periodic_task.local_tasks.kafka_check.kafka_disk_growth_check import check_kafka_disk_growth
from backend.db_periodic_task.local_tasks.kafka_check.kafka_zookeeper_check import check_kafka_zookeeper_affinity
from backend.db_report.enums.kafka_disk_growth_sub_type import KafkaDiskGrowthRunKind


@register_periodic_task(run_every=crontab(hour="9", minute="08"))
def kafka_zookeeper_affinity_task():
    """
    kafka zookeeper亲和性巡检
    """
    check_kafka_zookeeper_affinity()


@register_periodic_task(run_every=crontab(hour="9", minute="18"))
def kafka_broker_affinity_task():
    """
    kafka broker亲和性巡检
    """
    check_kafka_broker_affinity()


@register_periodic_task(run_every=crontab(hour="9", minute="25"))
def kafka_disk_growth_morning_task():
    """
    kafka 磁盘持续增长巡检（早间）：用昨天的完整日峰值判定
    """
    check_kafka_disk_growth(run_kind=KafkaDiskGrowthRunKind.MORNING.value)


@register_periodic_task(run_every=crontab(hour="16", minute="25"))
def kafka_disk_growth_afternoon_task():
    """
    kafka 磁盘持续增长巡检（午后）：用今天截至当时的峰值判定，用于周末前和下班前检查
    """
    check_kafka_disk_growth(run_kind=KafkaDiskGrowthRunKind.AFTERNOON.value)
