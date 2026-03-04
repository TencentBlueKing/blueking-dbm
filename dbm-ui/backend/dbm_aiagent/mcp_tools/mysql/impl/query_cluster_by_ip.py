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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance


def query_cluster_by_ip(ip_list: List[str], bk_cloud_id: int = 0) -> List[dict]:
    """根据 IP 列表查询关联的集群信息"""
    machines = Machine.objects.filter(ip__in=ip_list, bk_cloud_id=bk_cloud_id)
    machine_map = {m.ip: m for m in machines}

    results = []
    seen = set()

    for ip in ip_list:
        machine = machine_map.get(ip)
        if not machine:
            continue

        for inst in StorageInstance.objects.filter(machine=machine).prefetch_related("cluster"):
            for cluster in inst.cluster.all():
                key = (ip, cluster.id)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "ip": ip,
                        "cluster_id": cluster.id,
                        "cluster_domain": cluster.immute_domain,
                        "cluster_type": cluster.cluster_type,
                        "db_type": ClusterType.cluster_type_to_db_type(cluster.cluster_type),
                        "machine_type": machine.machine_type,
                        "bk_sub_zone": machine.bk_sub_zone,
                        "bk_sub_zone_id": machine.bk_sub_zone_id,
                        "bk_city": machine.bk_city.bk_idc_city_name,
                    }
                )

        for inst in ProxyInstance.objects.filter(machine=machine).prefetch_related("cluster"):
            for cluster in inst.cluster.all():
                key = (ip, cluster.id)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "ip": ip,
                        "cluster_id": cluster.id,
                        "cluster_domain": cluster.immute_domain,
                        "cluster_type": cluster.cluster_type,
                        "db_type": ClusterType.cluster_type_to_db_type(cluster.cluster_type),
                        "machine_type": machine.machine_type,
                        "bk_sub_zone": machine.bk_sub_zone,
                        "bk_sub_zone_id": machine.bk_sub_zone_id,
                        "bk_city": machine.bk_city.bk_idc_city_name,
                    }
                )

    return results
