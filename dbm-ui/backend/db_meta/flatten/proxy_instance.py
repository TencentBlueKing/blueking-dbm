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

from django.db.models import QuerySet

from backend.db_meta.enums import ClusterEntryType, MachineType
from backend.db_meta.flatten.machine import _machine_prefetch, _single_machine_cc_info, _single_machine_city_info
from backend.db_meta.flatten.parallel_helper import get_from_prefetch, parallel_fetch
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance

logger = logging.getLogger("root")


def _fetch_storage_data(proxy_ids: List[int]) -> Dict[int, List[Dict]]:
    def _worker(ids_chunk):
        storage_m2m_through = ProxyInstance.storageinstance.through
        result = defaultdict(list)
        for proxy_id, ip, port, is_stand_by in storage_m2m_through.objects.filter(
            proxyinstance_id__in=ids_chunk
        ).values_list(
            "proxyinstance_id",
            "storageinstance__machine__ip",
            "storageinstance__port",
            "storageinstance__is_stand_by",
        ):
            result[proxy_id].append({"ip": ip, "port": port, "is_stand_by": is_stand_by})
        return result

    return parallel_fetch(_worker, proxy_ids)


def _fetch_bind_entry_proxy_data(proxy_ids: List[int]) -> Dict[int, Dict]:
    bind_entry_through = ProxyInstance.bind_entry.through
    bind_entry_ids = set(
        bind_entry_through.objects.filter(proxyinstance_id__in=proxy_ids).values_list("clusterentry_id", flat=True)
    )
    bind_entry_proxy_info = {}
    for entry_id, ip, port in bind_entry_through.objects.filter(clusterentry_id__in=bind_entry_ids).values_list(
        "clusterentry_id",
        "proxyinstance__machine__ip",
        "proxyinstance__port",
    ):
        if entry_id not in bind_entry_proxy_info:
            bind_entry_proxy_info[entry_id] = {"ips": set(), "port": port}
        bind_entry_proxy_info[entry_id]["ips"].add(ip)
    return bind_entry_proxy_info


def _format_proxy_bind_entry_item(be, bind_ips: List[str], bind_port: int):
    if be.cluster_entry_type == ClusterEntryType.DNS:
        return {
            "domain": be.entry,
            "entry_role": be.role,
            "forward_entry_id": be.forward_to_id,
            "bind_ips": bind_ips,
            "bind_port": bind_port,
        }
    elif be.cluster_entry_type == ClusterEntryType.CLB:
        dt = get_from_prefetch(be.clbentrydetail_set)
        return {
            "clb_ip": dt.clb_ip,
            "clb_id": dt.clb_id,
            "listener_id": dt.listener_id,
            "clb_region": dt.clb_region,
            "bind_ips": bind_ips,
            "bind_port": bind_port,
        }
    elif be.cluster_entry_type == ClusterEntryType.POLARIS:
        dt = get_from_prefetch(be.polarisentrydetail_set)
        return {
            "polaris_name": dt.polaris_name,
            "polaris_l5": dt.polaris_l5,
            "polaris_token": dt.polaris_token,
            "alias_token": dt.alias_token,
            "bind_ips": bind_ips,
            "bind_port": bind_port,
        }
    else:
        return be.entry


def _build_bind_entry_with_proxy_info(ins: ProxyInstance, bind_entry_proxy_info: Dict[int, Dict]) -> Dict:
    bind_entry = defaultdict(list)
    for be in ins.bind_entry.all():
        be: ClusterEntry
        bp_info = bind_entry_proxy_info.get(be.id)
        if bp_info:
            bind_ips = list(bp_info["ips"])
            bind_port = bp_info["port"]
        else:
            bind_ips = []
            bind_port = 0
        bind_entry[be.cluster_entry_type].append(_format_proxy_bind_entry_item(be, bind_ips, bind_port))
    return dict(bind_entry)


def _build_proxy_base_info(ins: ProxyInstance) -> Dict:
    return {
        **_single_machine_city_info(ins.machine),
        **_single_machine_cc_info(ins.machine),
        "admin_port": ins.admin_port,
        "port": ins.port,
        "ip": ins.machine.ip,
        "db_module_id": ins.db_module_id,
        "bk_biz_id": ins.bk_biz_id,
        "cluster": "",
        "access_layer": ins.access_layer,
        "machine_type": ins.machine_type,
        "cluster_type": ins.cluster_type,
        "status": ins.status,
    }


def proxy_instance(proxies: QuerySet) -> List[Dict]:
    proxies_list: List[ProxyInstance] = list(
        proxies.prefetch_related(
            *_machine_prefetch(),
            "bind_entry",
            "bind_entry__clbentrydetail_set",
            "bind_entry__polarisentrydetail_set",
            "cluster",
        )
    )

    proxy_ids = [ins.id for ins in proxies_list]
    storage_by_proxy = _fetch_storage_data(proxy_ids)
    bind_entry_proxy_info = _fetch_bind_entry_proxy_data(proxy_ids)

    res = []
    for ins in proxies_list:
        info = _build_proxy_base_info(ins)

        if ins.machine_type == MachineType.SPIDER.value:
            info["spider_role"] = ins.tendbclusterspiderext.spider_role

        info["storageinstance"] = storage_by_proxy.get(ins.id, [])
        info["bind_entry"] = _build_bind_entry_with_proxy_info(ins, bind_entry_proxy_info)

        info["cluster_id"] = 0
        for cluster_obj in ins.cluster.all():
            cluster_obj: Cluster
            info["cluster"] = cluster_obj.immute_domain
            info["cluster_id"] = cluster_obj.id
            break

        res.append(info)

    return res
