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
from datetime import datetime, timedelta, timezone

from django.db.models import Count

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_monitor.constants import MySQLAutofixStep
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLAutofixTodo

from .proxy import autofix_proxy

logger = logging.getLogger("celery")


def autofix():
    """
    一个集群一个单
    """

    rs = (
        MySQLAutofixTodo.objects.filter(
            current_step=MySQLAutofixStep.IN_PLACE_AUTOFIX,
            inplace_ticket_status=MySQLAutofixTicketStatus.UNSUBMITTED,
            cluster_type__in=[ClusterType.TenDBHA],
            machine_type__in=[MachineType.PROXY],
            create_at__gte=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        .values(
            "check_id",
            "bk_cloud_id",
            "bk_biz_id",
            "ip",
        )
        .annotate(Count("port"))
    )

    # 按 ip 调度自愈
    for r in rs:
        autofix_proxy(r)
