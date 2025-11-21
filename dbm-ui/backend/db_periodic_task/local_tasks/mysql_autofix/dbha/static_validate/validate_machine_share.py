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
from typing import List

from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, Machine
from backend.db_monitor.models import MySQLDBHAEvent


def validate_machine_share(events: List[MySQLDBHAEvent]) -> List[MySQLDBHAEvent]:
    """
    机器共享检查
    假设一个集群 A 的机器 1.1.1.1, 在集群 A, B 共享
    则所有相关机器要么在 A, B 独占, 要么只在 A, B 共享
    # ToDo 这个还没写完
    """
    # bad_event_ids = []
    res = []
    for ev in events:
        try:
            machine = Machine.objects.get(bk_cloud_id=ev.bk_cloud_id, ip=ev.ip)
            if ev.machine_type in [MachineType.PROXY, MachineType.SPIDER]:
                relate_clusters = Cluster.objects.filter(proxyinstance__machine=machine)
            else:
                relate_clusters = Cluster.objects.filter(storageinstance__machine=machine)

            print(relate_clusters)
        except Exception as e:
            print(e)

    return res
