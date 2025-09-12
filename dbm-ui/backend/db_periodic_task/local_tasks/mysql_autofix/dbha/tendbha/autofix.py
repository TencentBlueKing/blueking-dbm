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
from typing import Dict, List

from backend.db_meta.enums import InstanceRole, MachineType
from backend.db_monitor.models import MySQLDBHAEvent
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbha.backend_autofix import repair_ro_slaves_replicate


def autofix(cluster_ids: List[int], events_by_machine_type: Dict[str, List[MySQLDBHAEvent]]):
    """ """
    if MachineType.PROXY.value in events_by_machine_type:
        # Todo 拼接新机重建单据参数
        pass

    if MachineType.BACKEND.value in events_by_machine_type:
        # Todo 拼接新机重建单据参数
        # 发起 ro slave 关系修复单据
        repair_ro_slaves_replicate(
            cluster_ids=cluster_ids,
            machine_type=MachineType.BACKEND.value,
            # 要针对 master 故障修复 ro slave 同步
            # 实际上传入的 events 的 check_id 应该都是相同的
            # 因为是 master, 只能有一台机器
            # ToDo 这里的 events 其实可以改成单对象
            events=[
                ev
                for ev in events_by_machine_type[MachineType.BACKEND.value]
                if ev.instance_role == InstanceRole.BACKEND_MASTER
            ]
            # events=events_by_machine_type[MachineType.BACKEND.value].filter(instance_role=InstanceRole.BACKEND_MASTER),
        )

    # ToDo 发起新机重建
