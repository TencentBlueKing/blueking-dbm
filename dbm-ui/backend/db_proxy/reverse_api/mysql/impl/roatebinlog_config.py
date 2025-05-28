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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import AccessLayer, MachineType
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.mysql_account_mixed import MySQLAccountMixed


def rotatebinlog_config(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> List:
    m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
    q = Q()
    q |= Q(**{"machine": m})

    if port_list:
        q &= Q(**{"port__in": port_list})

    if m.access_layer == AccessLayer.PROXY:
        qs = ProxyInstance.objects.filter(q).prefetch_related("cluster")
    else:
        qs = StorageInstance.objects.filter(q).prefetch_related("cluster")

    usermap = MySQLAccountMixed.mysql_static_account()

    res = []

    i: Union[StorageInstance, ProxyInstance]
    for i in qs.all():
        if not i.cluster.exists():
            continue

        if i.machine_type not in [
            MachineType.BACKEND,
            MachineType.REMOTE,
            MachineType.SINGLE,
        ]:  # , MachineType.SPIDER]:
            continue

        res.append(
            {
                "ip": ip,
                "port": i.port,
                "role": i.instance_inner_role,
                "bk_biz_id": int(i.bk_biz_id),
                "bk_cloud_id": m.bk_cloud_id,
                "cluster_domain": i.cluster.first().immute_domain,
                "cluster_id": i.cluster.first().id,
                "configs": DBConfigApi.query_conf_item(
                    {
                        "bk_biz_id": str(i.bk_biz_id),
                        "level_name": LevelName.MODULE,
                        "level_value": str(i.db_module_id),
                        "conf_file": "binlog_rotate.yaml",
                        "conf_type": "backup",
                        "namespace": i.cluster_type,
                        "format": FormatType.MAP_LEVEL,
                    }
                )["content"],
                "user": usermap["monitor_user"],
                "password": usermap["monitor_pwd"],
            }
        )

    return res
