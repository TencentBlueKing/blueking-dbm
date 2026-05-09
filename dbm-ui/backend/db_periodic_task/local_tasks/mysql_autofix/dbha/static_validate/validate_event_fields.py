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
from typing import List

from backend.db_meta.enums import ClusterType, ClusterTypeMachineTypeDefine, MachineType, MachineTypeInstanceRoleMap
from backend.db_monitor.models import MySQLDBHAEvent

logger = logging.getLogger("celery.mysql_dbha_autofix")


def validate_event_fields(events: List[MySQLDBHAEvent]) -> List[MySQLDBHAEvent]:
    """
    校验 event 各字段的逻辑正确性
    """
    res = []
    for ev in events:
        if ev.cluster_type not in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster]:
            logger.info(
                "[validate_fields] unsupported cluster_type: check_id=%d, ip=%s, cluster_type=%s",
                ev.check_id,
                ev.ip,
                ev.cluster_type,
            )
            ev.failed_validate_it(f"{ev.cluster_type} not supported")
            continue

        if ev.machine_type not in ClusterTypeMachineTypeDefine[ev.cluster_type]:
            logger.info(
                "[validate_fields] machine_type mismatch: check_id=%d, ip=%s, machine_type=%s, cluster_type=%s",
                ev.check_id,
                ev.ip,
                ev.machine_type,
                ev.cluster_type,
            )
            ev.failed_validate_it(f"{ev.machine_type} and {ev.cluster_type} not match")
            continue

        if ev.machine_type in [
            MachineType.BACKEND,
            MachineType.REMOTE,
            MachineType.SINGLE,
        ] and ev.instance_role not in MachineTypeInstanceRoleMap.get(ev.machine_type, []):
            logger.info(
                "[validate_fields] instance_role mismatch: check_id=%d, ip=%s, instance_role=%s, machine_type=%s",
                ev.check_id,
                ev.ip,
                ev.instance_role,
                ev.machine_type,
            )
            ev.failed_validate_it(f"{ev.instance_role} and {ev.machine_type} not match")
            continue

        res.append(ev)

    return res
