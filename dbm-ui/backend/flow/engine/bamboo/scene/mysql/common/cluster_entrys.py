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

from typing import Dict

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceInnerRole
from backend.db_meta.models import Cluster


def get_tendb_ha_entry(cluster_id: int) -> Dict:
    """
    获取tendb ha 集群相关的所有域名。
    @param cluster_id: tendb ha 集群id
    @return: dns map
    """
    cls = Cluster.objects.get(id=cluster_id)
    entry_map = {}
    master = cls.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
    standby_ins = cls.storageinstance_set.get(instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True)
    slave_ins = cls.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=False)
    entry_map["master_domain"] = cls.immute_domain
    # entry_map[master.machine.ip] = cls.immute_domain

    standby_ins_dns = standby_ins.bind_entry.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
    )
    if len(standby_ins_dns) == 0:
        standby_ins_dns = master.bind_entry.filter(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
        )
    if len(standby_ins_dns) >= 1:
        # todo 问题 standby 可能有多个域名
        entry_map["slave_domain"] = standby_ins_dns[0].entry

    for slave in slave_ins:
        if slave.machine.ip not in entry_map:
            entry_map[slave.machine.ip] = []
        slave_dns = slave.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value)
        slave_end_list = [slave_end.entry for slave_end in slave_dns]
        entry_map[slave.machine.ip].extend(slave_end_list)

    if standby_ins.machine.ip not in entry_map:
        entry_map[standby_ins.machine.ip] = [one.entry for one in standby_ins_dns]
    else:
        entry_map[standby_ins.machine.ip].extend([one.entry for one in standby_ins_dns])

    return entry_map
