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
from typing import List, Optional

from backend.components import DBPrivManagerApi
from backend.configuration.constants import DB_ADMIN_USER_MAP, DBType
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.utils.string import base64_decode


def get_instance_admin_password(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> dict:
    """
    目前不能正常工作
    """
    m = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=ip)
    if m.cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
        dbtype = DBType.MySQL
    elif m.cluster_type == ClusterType.TenDBCluster:
        dbtype = DBType.TenDBCluster
    else:
        raise Exception(f"not support cluster type: {m.cluster_type}")  # noqa

    if not port_list:
        if m.machine_type in [MachineType.BACKEND, MachineType.REMOTE, MachineType.SINGLE]:
            port_list = list(
                StorageInstance.objects.filter(
                    machine__ip=ip,
                    machine__bk_cloud_id=bk_cloud_id,
                ).values_list("port", flat=True)
            )

        elif m.machine_type == MachineType.SPIDER:
            port_list = list(
                ProxyInstance.objects.filter(
                    machine__ip=ip,
                    machine__bk_cloud_id=bk_cloud_id,
                ).values_list("port", flat=True)
            )
        else:
            raise Exception(f"not support machine type: {m.machine_type}")  # noqa

    instances = []
    for port in port_list:
        instances.append(
            {
                "ip": ip,
                "port": port,
            }
        )

    filters = {
        "bk_biz_id": m.bk_biz_id,
        "db_type": dbtype.value,
        "limit": 10,
        "offset": 0,
        "username": DB_ADMIN_USER_MAP[dbtype],
        "instances": instances,
    }

    admin_password_data = DBPrivManagerApi.get_mysql_admin_password(params=filters)
    admin_password_data["results"] = admin_password_data.pop("items")

    res = collections.defaultdict(dict)
    for data in admin_password_data["results"]:
        res[data["port"]]["username"] = data["username"]
        res[data["port"]]["password"] = base64_decode(data["password"])

    return res
