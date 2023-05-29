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
from typing import List

from django.db import transaction

from backend.constants import DEFAULT_TIME_ZONE
from backend.db_meta import request_validator
from backend.db_meta.enums import AccessLayer, InstanceStatus
from backend.db_meta.models import Machine, ProxyInstance

logger = logging.getLogger("flow")


@transaction.atomic
def create(
    proxies,
    creator: str = "",
    status: str = "",
    time_zone: str = DEFAULT_TIME_ZONE,
) -> List[ProxyInstance]:
    """
    ToDo: 冗余属性校验
    """
    proxies = request_validator.validated_proxy_list(proxies, allow_empty=False, allow_null=False)
    proxy_objs = []
    for proxy in proxies:
        proxy_ip = proxy["ip"]
        proxy_port = proxy["port"]
        version = proxy.get("version", "")

        machine_obj = Machine.objects.get(ip=proxy_ip)
        if machine_obj.access_layer != AccessLayer.PROXY:
            raise Exception("{} is not proxy layer".format(proxy_ip))

        real_status = status if status != "" else InstanceStatus.RUNNING

        proxy_objs.append(
            ProxyInstance.objects.create(
                machine=machine_obj,
                port=proxy_port,
                admin_port=proxy_port + 1000,
                db_module_id=machine_obj.db_module_id,
                bk_biz_id=machine_obj.bk_biz_id,
                access_layer=machine_obj.access_layer,
                machine_type=machine_obj.machine_type,
                cluster_type=machine_obj.cluster_type,
                status=real_status,
                creator=creator,
                time_zone=time_zone,
                version=version,
            )
        )
    return proxy_objs


@transaction.atomic
def update(proxies):
    proxies = request_validator.validated_proxy_update(data=proxies)

    for proxy in proxies:
        ip = proxy["ip"]
        port = proxy["port"]

        proxy_obj = ProxyInstance.objects.get(machine__ip=ip, port=port)

        new_status = proxy.get("status", proxy_obj.status)

        proxy_obj.status = new_status
        proxy_obj.save()
