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
from typing import List, Optional

from django.db.models import Q

from backend.db_meta.enums import AccessLayer, InstanceInnerRole, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance, TenDBClusterStorageSet


def list_instance_info(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> List[dict]:
    m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
    q = Q(machine=m)

    if port_list:
        q &= Q(port__in=port_list)

    if m.access_layer == AccessLayer.PROXY:
        return list_proxyinstance_info(q=q)
    else:
        return list_storageinstance_info(q=q)


def list_storageinstance_info(q: Q) -> List:
    instances = list(
        StorageInstance.objects.filter(q)
        .select_related("machine")
        .prefetch_related(
            "as_ejector__receiver__machine",
            "as_receiver__ejector__machine",
            "cluster",
        )
    )

    # 批量查 shard_id：收集所有 REMOTE 实例的 ejector_id，循环外一次查完
    remote_instances = [i for i in instances if i.machine_type == MachineType.REMOTE]

    inst_to_ejector_id = {}
    ejector_ids = set()
    for i in remote_instances:
        if i.instance_inner_role == InstanceInnerRole.MASTER:
            ejector_ids.add(i.id)
            inst_to_ejector_id[i.id] = i.id
        else:
            # as_receiver 已预取，不会再查库
            receiver_tuples = i.as_receiver.all()
            if receiver_tuples:
                ej_id = receiver_tuples[0].ejector_id
                ejector_ids.add(ej_id)
                inst_to_ejector_id[i.id] = ej_id

    ejector_to_shard = {}
    if ejector_ids:
        for ss in TenDBClusterStorageSet.objects.filter(
            storage_instance_tuple__ejector_id__in=ejector_ids
        ).select_related("storage_instance_tuple"):
            ej_id = ss.storage_instance_tuple.ejector_id
            if ej_id not in ejector_to_shard:
                ejector_to_shard[ej_id] = ss.shard_id

    res = []
    for i in instances:
        clusters = i.cluster.all()
        if not clusters:
            continue

        receivers = []
        for t in i.as_ejector.all():
            receivers.append(
                {
                    "ip": t.receiver.machine.ip,
                    "port": t.receiver.port,
                }
            )

        ejectors = []
        for t in i.as_receiver.all():
            ejectors.append(
                {
                    "ip": t.ejector.machine.ip,
                    "port": t.ejector.port,
                }
            )

        shard_id = 0
        if i.machine_type == MachineType.REMOTE:
            ej_id = inst_to_ejector_id.get(i.id)
            if ej_id is not None:
                shard_id = ejector_to_shard.get(ej_id, 0)

        res.append(
            {
                "ip": i.machine.ip,
                "port": i.port,
                "immute_domain": clusters[0].immute_domain,
                "phase": i.phase,
                "status": i.status,
                "access_layer": i.access_layer,
                "machine_type": i.machine_type,
                "is_standby": i.is_stand_by,
                "instance_role": i.instance_role,
                "instance_inner_role": i.instance_inner_role,
                "receivers": receivers,
                "ejectors": ejectors,
                "bk_instance_id": i.bk_instance_id,
                "bk_biz_id": i.bk_biz_id,
                "bk_cloud_id": i.machine.bk_cloud_id,
                "cluster_type": i.cluster_type,
                "cluster_id": clusters[0].id,
                "db_module_id": i.db_module_id,
                "shard_id": shard_id,
            }
        )

    return res


def list_proxyinstance_info(q: Q) -> List:
    instances = list(
        ProxyInstance.objects.filter(q)
        .select_related("machine", "tendbclusterspiderext")
        .prefetch_related("storageinstance__machine", "cluster")
    )

    res = []
    for i in instances:
        clusters = i.cluster.all()
        if not clusters:
            continue

        spider_ext = getattr(i, "tendbclusterspiderext", None)

        if (
            i.machine_type == MachineType.SPIDER
            and spider_ext
            and spider_ext.spider_role
            in [
                TenDBClusterSpiderRole.SPIDER_MNT,
                TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
            ]
        ):
            bk_instance_id = 0
        else:
            bk_instance_id = i.bk_instance_id

        spider_role = ""
        if i.machine_type == MachineType.SPIDER and spider_ext:
            spider_role = spider_ext.spider_role

        storageinstance_list = []
        for si in i.storageinstance.all():
            storageinstance_list.append(
                {
                    "ip": si.machine.ip,
                    "port": si.port,
                }
            )

        res.append(
            {
                "ip": i.machine.ip,
                "port": i.port,
                "immute_domain": clusters[0].immute_domain,
                "phase": i.phase,
                "status": i.status,
                "access_layer": i.access_layer,
                "machine_type": i.machine_type,
                "storageinstance_list": storageinstance_list,
                "bk_instance_id": bk_instance_id,
                "bk_biz_id": i.bk_biz_id,
                "bk_cloud_id": i.machine.bk_cloud_id,
                "cluster_type": i.cluster_type,
                "cluster_id": clusters[0].id,
                "db_module_id": i.db_module_id,
                "spider_role": spider_role,
            }
        )

    return res
