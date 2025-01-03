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

from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance


def list_instance_info(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> List[dict]:
    m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
    q = Q()
    q |= Q(**{"machine": m})

    if port_list:
        q &= Q(**{"port__in": port_list})

    if m.access_layer == AccessLayer.PROXY:
        res = list_proxyinstance_info(q=q)
    else:
        res = list_storageinstance_info(q=q)

    return res


def list_storageinstance_info(q: Q) -> List:
    res = []
    for i in StorageInstance.objects.filter(q).prefetch_related(
        "as_ejector__receiver__machine", "as_receiver__ejector__machine", "machine", "cluster"
    ):
        receivers = []
        ejectors = []
        for t in i.as_ejector.all():
            receivers.append(
                {
                    "ip": t.receiver.machine.ip,
                    "port": t.receiver.port,
                }
            )
        for t in i.as_receiver.all():
            ejectors.append(
                {
                    "ip": t.ejector.machine.ip,
                    "port": t.ejector.port,
                }
            )

        res.append(
            {
                "ip": i.machine.ip,
                "port": i.port,
                "immute_domain": i.cluster.all()[0].immute_domain,
                "phase": i.phase,
                "status": i.status,
                "access_layer": i.access_layer,
                "machine_type": i.machine_type,
                "is_standby": i.is_stand_by,
                "instance_role": i.instance_role,
                "instance_inner_role": i.instance_inner_role,
                "receivers": receivers,
                "ejectors": ejectors,
            }
        )

    return res


def list_proxyinstance_info(q: Q) -> List:
    res = []
    for i in ProxyInstance.objects.filter(q).prefetch_related("machine", "storageinstance__machine", "cluster"):
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
                "immute_domain": i.cluster.all()[0].immute_domain,
                "phase": i.phase,
                "status": i.status,
                "access_layer": i.access_layer,
                "machine_type": i.machine_type,
                "storageinstance_list": storageinstance_list,
            }
        )

    return res
