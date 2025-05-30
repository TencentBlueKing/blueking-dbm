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
from typing import Dict, List, Optional, Union

from django.db.models import Q

from backend.db_meta.enums import AccessLayer, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.flow.consts import SYSTEM_DBS
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.mysql_account_mixed import MySQLAccountMixed
from backend.flow.utils.mysql.act_payload.mixed.account_mixed.proxy_account_mixed import ProxyAccountMixed


def monitor_runtime_config(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> List[Dict]:
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
    if m.machine_type == MachineType.PROXY:
        proxyusermap = ProxyAccountMixed.proxy_admin_account()
        ac = {
            "proxy": {"user": usermap["monitor_access_all_user"], "password": usermap["monitor_access_all_pwd"]},
            "proxy_admin": {"user": proxyusermap["proxy_admin_user"], "password": proxyusermap["proxy_admin_pwd"]},
        }
    else:
        ac = {"mysql": {"user": usermap["monitor_user"], "password": usermap["monitor_pwd"]}}

    res = []

    i: Union[StorageInstance, ProxyInstance]
    for i in qs.all():
        if not i.cluster.exists():
            continue

        if m.machine_type == MachineType.SPIDER and i.tendbclusterspiderext.spider_role in [
            TenDBClusterSpiderRole.SPIDER_SLAVE,
            TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
        ]:
            bk_instance_id = 0
        else:
            bk_instance_id = i.bk_instance_id

        if m.access_layer == AccessLayer.PROXY:
            if m.machine_type == MachineType.PROXY:
                role = ""
            else:
                role = i.tendbclusterspiderext.spider_role
        else:
            role = i.instance_inner_role

        res.append(
            {
                "bk_biz_id": i.bk_biz_id,
                "ip": m.ip,
                "port": i.port,
                "bk_instance_id": bk_instance_id,
                "immute_domain": i.cluster.first().immute_domain,
                "machine_type": i.machine_type,
                "role": role,
                "bk_cloud_id": m.bk_cloud_id,
                "cluster_type": i.cluster_type,
                "auth": ac,
                "dba_sys_dbs": SYSTEM_DBS,
                "api_url": "http://127.0.0.1:9999",
            }
        )

    return res
