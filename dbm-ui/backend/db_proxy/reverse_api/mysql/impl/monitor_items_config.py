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

from backend.components import DBConfigApi
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance


def monitor_items_config(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> Dict[int, Dict]:
    m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
    q = Q()
    q |= Q(**{"machine": m})

    if port_list:
        q &= Q(**{"port__in": port_list})

    if m.access_layer == AccessLayer.PROXY:
        qs = ProxyInstance.objects.filter(q).prefetch_related("cluster")
    else:
        qs = StorageInstance.objects.filter(q).prefetch_related("cluster")

    res = {}

    i: Union[StorageInstance, ProxyInstance]
    for i in qs.all():
        if not i.cluster.exists():
            continue

        res[i.port] = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": f"{i.bk_biz_id}",
                "level_name": "cluster",
                "level_value": i.cluster.first().immute_domain,
                "conf_file": "items-config.yaml",
                "conf_type": "mysql_monitor",
                "namespace": "tendbha",
                "level_info": {"module": f"{i.db_module_id}"},
                "format": "map",
            }
        )["content"]

    return res
