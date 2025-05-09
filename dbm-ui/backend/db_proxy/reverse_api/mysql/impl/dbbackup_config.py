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
from typing import List, Optional, Union

from django.db.models import Q

from backend.db_meta.enums import AccessLayer, InstanceInnerRole, MachineType
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.mysql.mysql_bk_config import get_backup_ini_config, get_backup_options_config


def dbbackup_config(bk_cloud_id: int, ip: str, port_list: Optional[List[int]]) -> List:
    m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)

    if m.machine_type not in [MachineType.REMOTE, MachineType.BACKEND, MachineType.SINGLE, MachineType.SPIDER]:
        raise Exception("not support machine type: {}".format(m.machine_type))

    q = Q()
    q |= Q(**{"machine": m})

    if port_list:
        q &= Q(**{"port__in": port_list})

    if m.access_layer == AccessLayer.PROXY:
        qs = ProxyInstance.objects.filter(q).prefetch_related("cluster")
    else:
        qs = StorageInstance.objects.filter(q).prefetch_related("cluster")

    usermap = PayloadHandler.get_mysql_static_account()

    res = []

    i: Union[StorageInstance, ProxyInstance]
    for i in qs.all():
        ini = get_backup_ini_config(bk_biz_id=i.bk_biz_id, db_module_id=i.db_module_id, cluster_type=i.cluster_type)
        backup_options = get_backup_options_config(
            bk_biz_id=i.bk_biz_id,
            db_module_id=i.db_module_id,
            cluster_type=i.cluster_type,
            cluster_domain=i.cluster.first().immute_domain,
        )

        if m.machine_type == MachineType.SPIDER:
            role = i.tendbclusterspiderext.spider_role
        else:
            role = i.instance_inner_role

        shard_id = 0
        if m.machine_type == MachineType.REMOTE:
            if i.instance_inner_role == InstanceInnerRole.MASTER:
                shard_id = StorageInstanceTuple.objects.filter(ejector=i).first().tendbclusterstorageset.shard_id
            else:
                shard_id = StorageInstanceTuple.objects.get(receiver=i).tendbclusterstorageset.shard_id

        res.append(
            {
                "configs": ini,
                "options": backup_options,
                "ip": ip,
                "port": i.port,
                "role": role,
                "cluster_type": i.cluster_type,
                "bk_biz_id": int(i.bk_biz_id),
                "immute_domain": i.cluster.first().immute_domain,
                "cluster_id": i.cluster.first().id,
                "shard_id": shard_id,
                "user": usermap["backup_user"],
                "password": usermap["backup_pwd"],
                "bk_cloud_id": m.bk_cloud_id,
            }
        )

    return res
