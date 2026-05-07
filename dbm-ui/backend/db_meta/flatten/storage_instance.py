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
from typing import Dict, List, Tuple

from django.db.models import QuerySet

from backend.db_meta.enums import (
    ClusterEntryType,
    ClusterPhase,
    ClusterType,
    InstanceInnerRole,
    InstancePhase,
    InstanceStatus,
    TenDBClusterSpiderRole,
)
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.flatten.machine import _machine_prefetch, _single_machine_cc_info, _single_machine_city_info
from backend.db_meta.flatten.parallel_helper import get_from_prefetch, parallel_fetch
from backend.db_meta.models import ClusterEntry, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_meta.models.extra_process import ExtraProcessInstance

logger = logging.getLogger("root")


def _fetch_proxy_data(storage_ids: List[int]) -> Dict[int, List[Dict]]:
    def _worker(ids_chunk):
        proxy_m2m_through = ProxyInstance.storageinstance.through
        result = defaultdict(list)
        for storage_id, ip, port, admin_port, status, cluster_type, spider_role in proxy_m2m_through.objects.filter(
            storageinstance_id__in=ids_chunk
        ).values_list(
            "storageinstance_id",
            "proxyinstance__machine__ip",
            "proxyinstance__port",
            "proxyinstance__admin_port",
            "proxyinstance__status",
            "proxyinstance__cluster_type",
            "proxyinstance__tendbclusterspiderext__spider_role",
        ):
            if cluster_type == ClusterType.TenDBCluster and spider_role in [
                TenDBClusterSpiderRole.SPIDER_MNT,
                TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
            ]:
                continue
            result[storage_id].append({"ip": ip, "port": port, "admin_port": admin_port, "status": status})
        return result

    return parallel_fetch(_worker, storage_ids)


def _fetch_cluster_data(storage_ids: List[int]) -> Tuple[Dict[int, Tuple], List[int]]:
    cluster_m2m = StorageInstance.cluster.through
    cluster_by_storage = {}
    all_cluster_ids = []
    for inst_id, cluster_id, domain in cluster_m2m.objects.filter(storageinstance_id__in=storage_ids).values_list(
        "storageinstance_id", "cluster_id", "cluster__immute_domain"
    ):
        all_cluster_ids.append(cluster_id)
        if inst_id not in cluster_by_storage:
            cluster_by_storage[inst_id] = (cluster_id, domain)
    return cluster_by_storage, list(set(all_cluster_ids))


def _fetch_receiver_rows(storage_ids: List[int]) -> List[Tuple]:
    return list(
        StorageInstanceTuple.objects.filter(
            ejector_id__in=storage_ids,
            receiver__status=InstanceStatus.RUNNING,
            receiver__instance_inner_role=InstanceInnerRole.SLAVE,
            receiver__phase=InstancePhase.ONLINE,
        ).values_list(
            "ejector_id",
            "receiver_id",
            "receiver__machine__ip",
            "receiver__port",
            "receiver__status",
            "receiver__is_stand_by",
        )
    )


def _fetch_ejector_rows(storage_ids: List[int]) -> List[Tuple]:
    return list(
        StorageInstanceTuple.objects.filter(
            receiver_id__in=storage_ids,
            ejector__status=InstanceStatus.RUNNING,
            ejector__instance_inner_role__in=[InstanceInnerRole.MASTER, InstanceInnerRole.REPEATER],
            ejector__phase=InstancePhase.ONLINE,
        ).values_list(
            "receiver_id",
            "ejector_id",
            "ejector__machine__ip",
            "ejector__port",
            "ejector__status",
            "ejector__is_stand_by",
        )
    )


def _build_instance_cluster_map(
    storage_ids: List[int],
    cluster_by_storage: Dict[int, Tuple],
    receiver_rows: List[Tuple],
    ejector_rows: List[Tuple],
) -> Dict[int, int]:
    instance_cluster_map = {
        inst_id: cluster_by_storage[inst_id][0] for inst_id in storage_ids if inst_id in cluster_by_storage
    }
    related_ids = set()
    for _, other_id, *_ in receiver_rows:
        related_ids.add(other_id)
    for _, other_id, *_ in ejector_rows:
        related_ids.add(other_id)
    related_ids -= set(storage_ids)

    if related_ids:
        cluster_m2m = StorageInstance.cluster.through
        for inst_id, cluster_id in cluster_m2m.objects.filter(storageinstance_id__in=related_ids).values_list(
            "storageinstance_id", "cluster_id"
        ):
            if inst_id not in instance_cluster_map:
                instance_cluster_map[inst_id] = cluster_id
    return instance_cluster_map


def _group_with_cluster_match(rows: List[Tuple], instance_cluster_map: Dict[int, int]) -> Dict[int, List[Dict]]:
    result = defaultdict(list)
    for group_id, other_id, ip, port, status, is_stand_by in rows:
        g_cluster = instance_cluster_map.get(group_id)
        o_cluster = instance_cluster_map.get(other_id)
        if g_cluster is not None and o_cluster is not None and g_cluster == o_cluster:
            result[group_id].append({"ip": ip, "port": port, "status": status, "is_stand_by": is_stand_by})
    return result


def _fetch_dumper_data(all_cluster_ids: List[int]) -> Dict:
    dumper_infos: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
    for dumper in ExtraProcessInstance.objects.filter(
        cluster_id__in=all_cluster_ids, proc_type=ExtraProcessType.TBINLOGDUMPER, phase=ClusterPhase.ONLINE
    ):
        dumper_infos[dumper.cluster_id][dumper.extra_config.get("source_data_ip", "")].append(dumper)
    return dumper_infos


def _format_storage_bind_entry_item(be, bind_ips: List[str], bind_port: int):
    if be.cluster_entry_type == ClusterEntryType.DNS:
        return {"domain": be.entry, "entry_role": be.role, "bind_ips": bind_ips, "bind_port": bind_port}
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


def _build_bind_entry_from_prefetch(ins: StorageInstance) -> Dict:
    bind_entry = defaultdict(list)
    for be in ins.bind_entry.all():
        be: ClusterEntry
        storage_instance_list = list(be.storageinstance_set.all())
        bind_ips = list(set([ele.machine.ip for ele in storage_instance_list]))
        try:
            bind_port = storage_instance_list[0].port
        except (IndexError, AttributeError):
            bind_port = 0
        bind_entry[be.cluster_entry_type].append(_format_storage_bind_entry_item(be, bind_ips, bind_port))
    return dict(bind_entry)


def _build_storage_base_info(ins: StorageInstance) -> Dict:
    return {
        **_single_machine_city_info(ins.machine),
        **_single_machine_cc_info(ins.machine),
        "port": ins.port,
        "ip": ins.machine.ip,
        "db_module_id": ins.db_module_id,
        "bk_biz_id": ins.bk_biz_id,
        "cluster": "",
        "access_layer": ins.access_layer,
        "machine_type": ins.machine_type,
        "instance_role": ins.instance_role,
        "instance_inner_role": ins.instance_inner_role,
        "cluster_type": ins.cluster_type,
        "status": ins.status,
        "is_stand_by": ins.is_stand_by,
    }


def _attach_cluster_and_dumper(info: Dict, ins_id: int, ins_ip: str, cluster_by_storage: Dict, dumper_infos: Dict):
    info["cluster_id"] = 0
    cluster_info = cluster_by_storage.get(ins_id)
    if cluster_info:
        cluster_id, domain = cluster_info
        info["cluster"] = domain
        info["cluster_id"] = cluster_id
        info["tbinlogdumpers"] = [
            {"ip": dumper.ip, "port": dumper.listen_port}
            for dumper in dumper_infos.get(cluster_id, {}).get(ins_ip, [])
        ]


def storage_instance(storages: QuerySet) -> List[Dict]:
    storages_list: List[StorageInstance] = list(
        storages.prefetch_related(
            *_machine_prefetch(),
            "bind_entry",
            "bind_entry__clbentrydetail_set",
            "bind_entry__polarisentrydetail_set",
            "bind_entry__storageinstance_set",
            "bind_entry__storageinstance_set__machine",
        )
    )

    storage_ids = [ins.id for ins in storages_list]
    proxy_by_storage = _fetch_proxy_data(storage_ids)
    cluster_by_storage, all_cluster_ids = _fetch_cluster_data(storage_ids)
    receiver_rows = _fetch_receiver_rows(storage_ids)
    ejector_rows = _fetch_ejector_rows(storage_ids)
    instance_cluster_map = _build_instance_cluster_map(storage_ids, cluster_by_storage, receiver_rows, ejector_rows)
    receiver_by_storage = _group_with_cluster_match(receiver_rows, instance_cluster_map)
    ejector_by_storage = _group_with_cluster_match(ejector_rows, instance_cluster_map)
    dumper_infos = _fetch_dumper_data(all_cluster_ids)

    res = []
    for ins in storages_list:
        info = _build_storage_base_info(ins)
        info["receiver"] = receiver_by_storage.get(ins.id, [])
        info["ejector"] = ejector_by_storage.get(ins.id, [])
        info["bind_entry"] = _build_bind_entry_from_prefetch(ins)
        info["proxyinstance_set"] = proxy_by_storage.get(ins.id, [])
        _attach_cluster_and_dumper(info, ins.id, ins.machine.ip, cluster_by_storage, dumper_infos)
        res.append(info)

    return res
