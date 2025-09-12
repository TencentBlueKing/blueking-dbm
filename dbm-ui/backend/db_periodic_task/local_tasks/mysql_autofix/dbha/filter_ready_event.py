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

from collections import defaultdict
from typing import List, Tuple

from backend.db_meta.enums import MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_monitor.models import MySQLDBHAEvent


def filter_ready_events(events: List[MySQLDBHAEvent]) -> List[MySQLDBHAEvent]:
    """
    获取准备好的 events
    就是在机器所有实例的 events 都到达的
    """
    not_ready_check_ids = []

    port_counter_dict = defaultdict(set)
    for ev in events:
        port_counter_dict[__event_compound_key(ev)].add(ev.port)

    for k, v in port_counter_dict.items():
        cnt = len(v)
        check_id, ip, machine_type, bk_cloud_id = __restore_from_compound_key(k)

        if machine_type in [MachineType.PROXY, MachineType.SINGLE]:
            insts = ProxyInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)
        else:
            insts = StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)

        if insts.count() != cnt:
            not_ready_check_ids.append(check_id)

    # 未准备好的 event 置空 af_uuid, 让它们可以在下一轮被选中
    MySQLDBHAEvent.objects.filter(check_id__in=not_ready_check_ids).update(af_uuid=None)

    return [e for e in events if e.check_id not in not_ready_check_ids]


def __event_compound_key(event: MySQLDBHAEvent) -> str:
    return f"{event.check_id}-{event.ip}-{event.machine_type}-{event.bk_cloud_id}"


def __restore_from_compound_key(k: str) -> Tuple[int, str, str, int]:
    split_key = k.split("-")
    return int(split_key[0]), split_key[1], split_key[2], int(split_key[3])
