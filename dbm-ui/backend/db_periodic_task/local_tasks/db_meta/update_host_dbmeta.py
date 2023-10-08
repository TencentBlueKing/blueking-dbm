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
import json
import logging

from celery.schedules import crontab

from backend.components import CCApi
from backend.db_meta.models import Cluster, Machine
from backend.db_meta.models.cluster_monitor import SyncFailedMachine
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.dbm_init.constants import CC_HOST_DBM_ATTR

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute="*/2"))
def update_host_dbmeta(bk_biz_id=None, cluster_id=None, cluster_ips=None, dbm_meta=None):
    """
    更新集群主机的dbm_meta属性
    TODO 应该挪到转移主机的时候做，每两分钟对全量主机更新一次 db_meta，太频繁了
    """

    now = datetime.datetime.now()
    logger.info("[update_host_dbmeta] start update begin: %s", now)

    # 0为默认的无效machine
    failed_host_ids = list(SyncFailedMachine.objects.all().values_list("bk_host_id", flat=True)) + [0]

    # 支持业务级别的更新
    machines = Machine.objects.all()
    if bk_biz_id:
        machines = machines.filter(bk_biz_id=bk_biz_id)

    machines = machines.exclude(
        bk_host_id__in=failed_host_ids,
    ).order_by("-create_at")

    if cluster_id:
        cluster = Cluster.objects.get(pk=cluster_id)
        cluster_bk_host_ids = set(
            list(cluster.storageinstance_set.values_list("machine__bk_host_id", flat=True))
            + list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True))
        )
        machines = Machine.objects.filter(bk_host_id__in=cluster_bk_host_ids)

    if cluster_ips:
        machines = machines.filter(ip__in=cluster_ips)

    # 批量更新接口限制最多500条，这里取456条
    STEP = 456
    updated_hosts, failed_updates = [], []
    machine_count = machines.count()
    for step in range(machine_count // STEP + 1):
        updates = []
        for machine in machines[step * STEP : (step + 1) * STEP]:
            cc_dbm_meta = machine.dbm_meta if dbm_meta is None else dbm_meta
            updates.append(
                {"properties": {CC_HOST_DBM_ATTR: json.dumps(cc_dbm_meta)}, "bk_host_id": machine.bk_host_id}
            )
        updated_hosts.extend(updates)

        try:
            CCApi.batch_update_host({"update": updates}, use_admin=True)
        except Exception as e:  # pylint: disable=wildcard-import
            failed_updates.extend(updates)
            logger.error("[update_host_dbmeta] batch update exception: %s (%s)", updates, e)

    # 容错处理：逐个更新，避免批量更新误伤有效ip
    for fail_update in failed_updates:
        try:
            CCApi.update_host(
                {"bk_host_id": fail_update["bk_host_id"], "data": fail_update["properties"]}, use_admin=True
            )
        except Exception as e:  # pylint: disable=wildcard-import
            # 记录异常ip，下次任务直接排除掉，尽量走批量更新
            SyncFailedMachine.objects.get_or_create(bk_host_id=fail_update["bk_host_id"], error=str(e))
            logger.error("[update_host_dbmeta] single update error: %s (%s)", fail_update, e)

    logger.info(
        "[update_host_dbmeta] finish update end: %s, update_cnt: %s",
        datetime.datetime.now() - now,
        len(updated_hosts),
    )
