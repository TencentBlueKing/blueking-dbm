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
from typing import List

from django.db.models import Q

from backend.db_meta import request_validator, validators
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER

logger = logging.getLogger("root")


def query_instances(payloads: List):
    """
    可输入IP、Addr
    前置检查,检测实例、ip是否被使用
    [1.1.1.1#30000,1.1.1.2]
    """
    payloads = request_validator.validated_str_list(payloads)

    queies = Q()

    for ad in payloads:
        if validators.ipv4(ad) or validators.ipv6(ad):
            queies |= Q(**{"machine__ip": ad})
        elif validators.instance(ad):
            ip, port = ad.split(IP_PORT_DIVIDER)
            queies |= Q(**{"machine__ip": ip, "port": port})

    instances = list(ProxyInstance.objects.filter(queies).values()) if queies else []
    instances += list(StorageInstance.objects.filter(queies).values())

    return instances


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
