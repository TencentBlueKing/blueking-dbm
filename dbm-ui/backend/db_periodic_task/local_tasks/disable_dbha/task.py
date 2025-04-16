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
import datetime
import logging

from celery.schedules import crontab

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.models import Cluster, ClusterDBHAExt
from backend.db_periodic_task.local_tasks import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute="*"))
def update_disable_dbha_config():
    """
    有的业务要整个禁用 dbha
    但是现在的设计是按集群来的, 这些业务有新集群会漏配置
    短时间内又没时间从头搞一遍设计
    先搞个 task 高频更新下禁用 dbha 的表
    """
    disable_dbha_config = (
        SystemSettings.get_setting_value(SystemSettingsEnum.DISABLE_DBHA_APPS_CLUSTER_TYPE.value) or {}
    )
    # "bk_biz_id": ["cluster_types"]
    # {
    #    "123": ["tendbha", "sqlsvr"],
    #    "456": ["tendbcluster"],
    # }

    now = datetime.datetime.now()
    for bk_biz_id, cluster_types in disable_dbha_config.items():
        for c in Cluster.objects.filter(bk_biz_id=int(bk_biz_id), cluster_type__in=cluster_types):
            ClusterDBHAExt.objects.update_or_create(
                defaults={
                    "creator": "admin",
                    "updater": "admin",
                    "end_time": datetime.timedelta(days=3000) + now,
                },
                cluster_id=c.id,
            )
