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

from django.core.management.base import BaseCommand

from backend.db_monitor.constants import AlertSourceEnum
from backend.db_monitor.models import MonitorPolicy

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "告警数据来源字段补充"

    def handle(self, *args, **options):
        event_policies = set()
        time_series_policies = set()

        for policy in MonitorPolicy.objects.all():
            for item in policy.details["items"]:
                for query_config in item["query_configs"]:
                    if query_config["data_type_label"] == "event":
                        event_policies.add(policy.id)
                    else:
                        time_series_policies.add(policy.id)

        MonitorPolicy.objects.filter(id__in=event_policies).update(alert_source=AlertSourceEnum.EVENT.value)
        MonitorPolicy.objects.filter(id__in=time_series_policies).update(
            alert_source=AlertSourceEnum.TIME_SERIES.value
        )
