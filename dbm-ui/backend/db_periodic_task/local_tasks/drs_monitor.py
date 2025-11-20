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
from celery.schedules import crontab
from django.utils.translation import gettext_lazy as _

from backend.components import DRSApi
from backend.components.bkmonitorv3.client import BKMonitorV3EventApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import StorageInstance
from backend.db_monitor.constants import MonitorEventType
from backend.db_monitor.dataclass import BaseEventBody, MonitorEvent
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_proxy.models import DBExtension
from backend.exceptions import ApiRequestError
from backend.flow.consts import InstanceStatus


@register_periodic_task(run_every=crontab(minute="*"))
def drs_monitor():
    for bk_cloud_id in DBExtension.objects.only("bk_cloud_id").distinct().values_list("bk_cloud_id", flat=True):
        rand_instance = (
            StorageInstance.objects.filter(
                cluster_type__in=[ClusterType.TenDBHA, ClusterType.TenDBSingle, ClusterType.TenDBCluster],
                status=InstanceStatus.RUNNING,
                instance_inner_role=InstanceInnerRole.SLAVE,
            )
            .order_by("?")
            .first()
        )

        if not rand_instance:
            continue

        try:
            DRSApi.rpc(
                {
                    "addresses": [rand_instance.ip_port],
                    "cmds": ["select 1"],
                    "force": False,
                    "bk_cloud_id": bk_cloud_id,
                    "query_timeout": 1,
                }
            )
        except ApiRequestError as e:
            BKMonitorV3EventApi.send_event(
                [
                    MonitorEvent(
                        event_name=MonitorEventType.DRS_REQUEST_FAILED,
                        target=_("云区域 {}".format(bk_cloud_id)),
                        event=BaseEventBody(content=f"{e}"),
                        dimension={"bk_cloud_id": bk_cloud_id},
                        timestamp=0,
                    )
                ]
            )
