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

from backend.db_dirty.constants import PoolType
from backend.db_dirty.handlers import DBDirtyMachineHandler
from backend.db_dirty.models import DirtyMachine
from backend.db_periodic_task.local_tasks import register_periodic_task


@register_periodic_task(run_every=crontab(minute="0", hour="10", day_of_week="1-5"))
def auto_recycle_dissolve_hosts():
    # 查询所有待回收的机器，分批回收
    recycle_hosts = list(DirtyMachine.objects.filter(pool=PoolType.Recycle).values_list("bk_host_id", flat=True))
    batch = 100
    for index in range(0, len(recycle_hosts), batch):
        DBDirtyMachineHandler.recycle_dissolve_hosts(recycle_hosts[index : index + batch])
