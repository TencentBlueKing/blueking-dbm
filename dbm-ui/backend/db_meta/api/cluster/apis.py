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
from collections import defaultdict
from typing import Dict, List

from django.db.models import Q

from backend.db_meta import request_validator
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry, Machine

logger = logging.getLogger("root")


def query_instances(ip: str) -> Dict:
    ip = request_validator.validated_ip(ip)

    queries = Q(**{"storageinstance__machine__ip": ip}) | Q(**{"proxyinstance__machine__ip": ip})
    qs = Cluster.objects.filter(queries)

    if qs.exists():
        cluster = qs.first()
        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": cluster.bk_biz_id,
            "db_module_id": cluster.db_module_id,
            "cluster_type": cluster.cluster_type,
        }
    else:
        return {}


def domain_exists(domains: List[str]) -> Dict[str, bool]:
    domains = request_validator.validated_domain_list(domains, allow_empty=False)

    res = {}
    for dm in domains:
        res[dm] = False
    for obj in ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS, entry__in=domains):
        res[obj.entry] = True

    return res


def query_cluster_by_hosts(hosts: List):
    """根据提供的IP 查询集群信息

    Args:
        hosts (List): ip 列表
    """
    hosts = request_validator.validated_str_list(hosts)
    machine_cluster = defaultdict(dict)
    # 这里仅支持同实例角色，多角色的TODO
    machine_ports = {}
    for mahcine_obj in Machine.objects.prefetch_related("storageinstance_set", "proxyinstance_set").filter(
        ip__in=hosts
    ):
        for storage in mahcine_obj.storageinstance_set.prefetch_related("cluster"):  # 这里存在多个实例
            if not machine_ports.get(storage.machine.ip):
                machine_ports[storage.machine.ip] = []
            machine_ports[storage.machine.ip].append(storage.port)
            for cluster in storage.cluster.all():  # 大部分就只有一个集群
                key = storage.machine.ip + "." + cluster.immute_domain
                if not machine_cluster.get(key):
                    machine_cluster[key] = {
                        "bk_biz_id": storage.machine.bk_biz_id,
                        "bk_cloud_id": storage.machine.bk_cloud_id,
                        "ip": storage.machine.ip,
                        "bk_host_id": storage.machine.bk_host_id,
                        "instance_role": storage.instance_role,
                        "machine_type": storage.machine.machine_type,
                        "cs_ports": [
                            cstorage.port
                            for cstorage in cluster.storageinstance_set.filter(machine__ip=storage.machine.ip)
                        ],
                        "cluster": cluster.immute_domain,
                        "cluster_name": cluster.name,
                        "cluster_id": cluster.id,
                        "cluster_type": cluster.cluster_type,
                        "major_version": cluster.major_version,
                    }
        for storage in mahcine_obj.proxyinstance_set.prefetch_related("cluster"):  # 这里存在多个实例
            if not machine_ports.get(storage.machine.ip):
                machine_ports[storage.machine.ip] = []
            machine_ports[storage.machine.ip].append(storage.port)
            for cluster in storage.cluster.all():  # 大部分就只有一个集群
                key = storage.machine.ip + "." + cluster.immute_domain
                if not machine_cluster.get(key):
                    machine_cluster[key] = {
                        "bk_biz_id": storage.machine.bk_biz_id,
                        "bk_cloud_id": storage.machine.bk_cloud_id,
                        "ip": storage.machine.ip,
                        "bk_host_id": storage.machine.bk_host_id,
                        "instance_role": storage.machine_type,
                        "machine_type": storage.machine.machine_type,
                        "cs_ports": [
                            cstorage.port
                            for cstorage in cluster.storageinstance_set.filter(machine__ip=storage.machine.ip)
                        ],
                        "cluster": cluster.immute_domain,
                        "cluster_name": cluster.name,
                        "cluster_id": cluster.id,
                        "cluster_type": cluster.cluster_type,
                        "major_version": cluster.major_version,
                    }

    for machine in machine_cluster.values():
        machine["ports"] = machine_ports.get(machine["ip"])
    return machine_cluster.values()
