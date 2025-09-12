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
__all__ = ["aggregate_events"]

import json
from typing import Dict, List, Tuple

from black.trans import defaultdict

from backend.db_monitor.models import MySQLDBHAEvent


def aggregate_events(events: List[MySQLDBHAEvent]) -> Dict[str, Dict[str, List[MySQLDBHAEvent]]]:
    """
    聚合关联 events
    {
      "相关集群": {
        "机器类型": List[MySQLDBHAEvent]
        ...
      }
      ...
    }
    """
    res = {}

    aggregate_cluster_ids = defaultdict(set)
    for ev in events:
        k = __event_aggregate_key(event=ev)
        aggregate_cluster_ids[k].add(ev.cluster_id)

    for k, v in aggregate_cluster_ids.items():
        check_id, machine_type = __restore_from_aggregate_key(k)
        cluster_ids = list(v)
        cluster_ids.sort()

        cluster_ids_str = json.dumps(cluster_ids)

        if cluster_ids_str not in res:
            res[cluster_ids_str] = {}

        if machine_type not in res[cluster_ids_str]:
            res[cluster_ids_str][machine_type] = []

        res[cluster_ids_str][machine_type].extend([e for e in events if e.check_id == check_id])

    return res


def __event_aggregate_key(event: MySQLDBHAEvent) -> str:
    return f"{event.check_id}-{event.machine_type}"


def __restore_from_aggregate_key(k: str) -> Tuple[int, str]:
    split_key = k.split("-")
    return int(split_key[0]), split_key[1]
