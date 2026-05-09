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
from typing import Dict, List

from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_monitor.models import MySQLDBHAEvent
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbha.backend_autofix import (
    repair_ro_slaves_replicate,
    replace_slave,
)
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbha.proxy_autofix import replace_proxy

logger = logging.getLogger("celery.mysql_dbha_autofix")


def autofix(cluster_ids: List[int], events_by_machine_type: Dict[str, List[MySQLDBHAEvent]]):
    """ """
    logger.info("[tendbha.autofix] cluster_ids=%s, machine_types=%s", cluster_ids, list(events_by_machine_type.keys()))

    if MachineType.PROXY.value in events_by_machine_type:
        logger.info("[tendbha.autofix] dispatching replace_proxy, cluster_ids=%s", cluster_ids)
        replace_proxy(
            cluster_ids=cluster_ids,
            machine_type=MachineType.PROXY,
            events=events_by_machine_type[str(MachineType.PROXY.value)],
        )

    if MachineType.BACKEND.value in events_by_machine_type:
        master_events = [
            ev
            for ev in events_by_machine_type[str(MachineType.BACKEND.value)]
            if ev.instance_role == InstanceRole.BACKEND_MASTER
        ]
        if master_events:
            logger.info(
                "[tendbha.autofix] dispatching repair_ro_slaves_replicate, cluster_ids=%s, master_ips=%s",
                cluster_ids,
                [ev.ip for ev in master_events],
            )
        # 发起 ro slave 关系修复单据
        repair_ro_slaves_replicate(
            cluster_ids=cluster_ids,
            machine_type=MachineType.BACKEND,
            events=master_events,
        )

        # 只要是 backend 的 dbha, 现在坏的肯定是 slave
        # 重建就好了
        logger.info("[tendbha.autofix] dispatching replace_slave, cluster_ids=%s", cluster_ids)
        replace_slave(
            cluster_ids=cluster_ids,
            machine_type=MachineType.BACKEND,
            events=events_by_machine_type[str(MachineType.BACKEND.value)],
        )
