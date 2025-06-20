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

from backend.db_meta.enums import AccessLayer, MachineType
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.flow.consts import UserName
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.mysql_account_mixed import MySQLAccountMixed
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.proxy_account_mixed import ProxyAccountMixed


def exporter_config(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> List:
    m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
    q = Q()
    q |= Q(**{"machine": m})

    if port_list:
        q &= Q(**{"port__in": port_list})

    if m.access_layer == AccessLayer.PROXY:
        qs = ProxyInstance.objects.filter(q).prefetch_related("cluster")
    else:
        qs = StorageInstance.objects.filter(q).prefetch_related("cluster")

    res = []

    i: Union[StorageInstance, ProxyInstance]
    for i in qs.all():
        instance_role = ""
        if i.machine_type == MachineType.PROXY:
            usermap = ProxyAccountMixed.proxy_admin_account()
            user = usermap["proxy_admin_user"]
            password = usermap["proxy_admin_pwd"]
        else:
            usermap = MySQLAccountMixed.mysql_static_account(UserName.MONITOR)
            user = usermap["monitor_user"]
            password = usermap["monitor_pwd"]
            if i.machine_type == MachineType.SPIDER:
                instance_role = i.tendbclusterspiderext.spider_role
            else:
                # instance_role: remote_slave, instance_inner_role: slave
                instance_role = i.instance_role

        res.append(
            {
                "ip": ip,
                "port": i.port,
                "machine_type": i.machine_type,
                "user": user,
                "password": password,
                "instance_role": instance_role,
            }
        )

    return res
