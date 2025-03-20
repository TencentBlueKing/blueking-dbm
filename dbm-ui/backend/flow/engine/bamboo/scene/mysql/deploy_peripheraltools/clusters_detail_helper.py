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
import collections
from typing import Dict, List, Tuple

from backend.db_meta.enums import AccessLayer


def is_empty_clusters_detail(clusters_detail: Dict[str, Dict[str, List[str]]]) -> bool:
    if clusters_detail_ips(clusters_detail):
        return False
    return True


def clusters_detail_ips(clusters_detail: Dict[str, Dict[str, List[str]]]) -> List[str]:
    """
    返回 ip 列表
    """
    res = []

    for _, cluster_detail in clusters_detail.items():
        for _, instance_list in cluster_detail.items():
            res.extend([i.split(":")[0] for i in instance_list])

    return list(set(res))


def clusters_detail_ips_by_access_layer(
    clusters_detail: Dict[str, Dict[str, List[str]]]
) -> Tuple[List[str], List[str]]:
    """
    按 access layer 返回 ip 列表
    """
    proxy_ips = []
    storage_ips = []

    for _, cluster_detail in clusters_detail.items():
        for access_layer, instances in cluster_detail.items():
            for instance in instances:
                ip = instance.split(":")[0]
                if access_layer == AccessLayer.PROXY:
                    proxy_ips.append(ip)
                else:
                    storage_ips.append(ip)
    return list(set(proxy_ips)), list(set(storage_ips))


def clusters_detail_ip_ports_by_access_layer(
    clusters_detail: Dict[str, Dict[str, List[str]]]
) -> Tuple[Dict[str, List[int]], Dict[str, List[int]]]:
    """
    按 access layer 返回 ip:port_list
    """
    proxy_ip_port_dict = collections.defaultdict(list)
    storage_ip_port_dict = collections.defaultdict(list)

    for _, cluster_detail in clusters_detail.items():
        for access_layer, instances in cluster_detail.items():
            for instance in instances:
                ip = instance.split(":")[0]
                port = int(instance.split(":")[1])

                if access_layer == AccessLayer.PROXY:
                    proxy_ip_port_dict[ip].append(port)
                else:
                    storage_ip_port_dict[ip].append(port)

    return proxy_ip_port_dict, storage_ip_port_dict
