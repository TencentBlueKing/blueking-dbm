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
__all__ = ["filter_ready_events"]

import logging
from collections import defaultdict
from typing import List

from backend.db_meta.enums import MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_monitor.models import MySQLDBHAEvent

logger = logging.getLogger("celery.mysql_dbha_autofix")


def filter_ready_events(events: List[MySQLDBHAEvent]) -> List[MySQLDBHAEvent]:
    """
    获取准备好的 events
    就是在机器所有实例的 events 都到达的
    """
    if not events:
        return []

    not_ready_check_ids = []

    port_counter_dict = defaultdict(set)
    for ev in events:
        key = (ev.check_id, ev.ip, ev.machine_type, ev.bk_cloud_id)
        port_counter_dict[key].add(ev.port)

    for (check_id, ip, machine_type, bk_cloud_id), ports in port_counter_dict.items():
        try:
            if machine_type in [MachineType.PROXY, MachineType.SPIDER]:
                insts = ProxyInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)
            else:
                insts = StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)

            expected_count = insts.count()
            if expected_count != len(ports):
                logger.info(
                    "[filter_ready] not ready: check_id=%d, ip=%s, machine_type=%s, bk_cloud_id=%d, "
                    "reported_ports=%s, expected_count=%d",
                    check_id,
                    ip,
                    machine_type,
                    bk_cloud_id,
                    ports,
                    expected_count,
                )
                not_ready_check_ids.append(check_id)
        except Exception:  # noqa
            logger.exception("[filter_ready] failed to check check_id=%d, ip=%s", check_id, ip)
            not_ready_check_ids.append(check_id)

    # 未准备好的 event 置空 af_uuid, 让它们可以在下一轮被选中
    if not_ready_check_ids:
        MySQLDBHAEvent.objects.filter(check_id__in=not_ready_check_ids, af_uuid=events[0].af_uuid).update(af_uuid="")
        logger.info("[filter_ready] reset af_uuid for not_ready check_ids=%s", not_ready_check_ids)

    return [e for e in events if e.check_id not in not_ready_check_ids]
