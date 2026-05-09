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
import logging
from collections import defaultdict
from typing import Dict, List

from backend.db_monitor.models import MySQLDBHAEvent

logger = logging.getLogger("celery.mysql_dbha_autofix")


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
    if not events:
        return {}

    res = {}

    aggregate_cluster_ids = defaultdict(set)
    for ev in events:
        key = (ev.check_id, ev.machine_type)
        aggregate_cluster_ids[key].add(ev.cluster_id)

    for (check_id, machine_type), cluster_id_set in aggregate_cluster_ids.items():
        cluster_ids = sorted(cluster_id_set)
        cluster_ids_str = json.dumps(cluster_ids)

        if cluster_ids_str not in res:
            res[cluster_ids_str] = {}

        if machine_type not in res[cluster_ids_str]:
            res[cluster_ids_str][machine_type] = []

        res[cluster_ids_str][machine_type].extend([e for e in events if e.check_id == check_id])

        logger.info(
            "[aggregate] check_id=%d, machine_type=%s, cluster_ids=%s",
            check_id,
            machine_type,
            cluster_ids,
        )

    logger.info("[aggregate] result: %d groups, keys=%s", len(res), list(res.keys()))
    return res
