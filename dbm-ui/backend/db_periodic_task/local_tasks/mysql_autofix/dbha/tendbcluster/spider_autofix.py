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

from backend.db_meta.enums import MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import ProxyInstance
from backend.db_monitor.models import MySQLDBHAEvent


def replace_spider(cluster_ids: List[int], machine_type: MachineType, events: List[MySQLDBHAEvent]):
    """
    由于历史遗留问题, 部分 spider slave 存在集群间共享
    所以这个 cluster_ids 其实没多大用
    需要重新按 spider role 演算
    """
    spider_master_events = []
    spider_slave_events = []
    spider_master_cluster_ids = set()
    spider_slave_cluster_ids = set()
    for ev in events:
        spider_role = ProxyInstance.objects.get(machine__ip=ev.ip, port=ev.port).tendbclusterspiderext.spider_role
        if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
            spider_master_events.append(ev)
            spider_master_cluster_ids.add(ev.cluster_id)
        elif spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE:
            spider_slave_events.append(ev)
            spider_slave_cluster_ids.add(ev.cluster_id)
        else:  # [spider_mnt, spider_mnt_slave, spider_ctl] 这 3 个不应该出现
            pass

    if spider_master_events:
        replace_spider_master(
            cluster_ids=list(spider_master_cluster_ids), machine_type=machine_type, events=spider_master_events
        )

    if spider_slave_events:
        replace_spider_slave(
            cluster_ids=list(spider_slave_cluster_ids), machine_type=machine_type, events=spider_slave_events
        )


def replace_spider_master(cluster_ids: List[int], machine_type: MachineType, events: List[MySQLDBHAEvent]):
    pass


def replace_spider_slave(cluster_ids: List[int], machine_type: MachineType, events: List[MySQLDBHAEvent]):
    pass
