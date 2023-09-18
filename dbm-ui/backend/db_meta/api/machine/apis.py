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
from typing import List, Optional

from django.db import transaction

from backend import env
from backend.components import CCApi
from backend.db_meta import request_validator
from backend.db_meta.enums import MachineType, MachineTypeAccessLayerMap, machine_type_to_cluster_type
from backend.db_meta.models import BKCity, Machine
from backend.flow.utils.mysql.bk_module_operate import transfer_host_in_cluster_module

logger = logging.getLogger("root")


@transaction.atomic
def create(
    bk_cloud_id: int,
    machines: Optional[List] = None,
    creator: str = "",
):
    """
    :param machines: 机器列表
    [{"ip": "127.0.0.0", "bk_biz_id": 2, "machine_type": "backend"}]
    :param creator: 创建者
    :param bk_cloud_id: 云区域id
    """
    machines = request_validator.validated_machine_create(machines, allow_empty=False, allow_null=False)

    ips = [m["ip"] for m in machines]
    kwargs = {
        "fields": [
            "bk_host_id",
            "bk_os_name",
            "bk_host_innerip",
            "idc_city_name",
            "idc_city_id",
            "bk_idc_area",
            "bk_idc_area_id",
            "sub_zone_id",
            "sub_zone",
            "rack_id",
            "rack",
            "bk_svr_device_cls_name",
            "idc_name",
            "idc_id",
            "bk_cloud_id",
            "net_device_id",
        ],
        "host_property_filter": {
            "condition": "AND",
            "rules": [
                {"field": "bk_host_innerip", "operator": "in", "value": ips},
                {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
            ],
        },
    }

    res = CCApi.list_hosts_without_biz(kwargs, use_admin=True)

    inf_dict = {}
    for inf in res["info"]:
        inf_dict[inf["bk_host_innerip"]] = inf

    not_found_ips = list(set(ips) - set(inf_dict.keys()))
    if not_found_ips:
        raise Exception("{} not found in bk cc".format(not_found_ips))
    for machine in machines:
        ip = machine["ip"]
        inf = inf_dict[ip]
        bk_idc_city_id = inf.get("idc_city_id") or 0

        bk_city_obj = BKCity.objects.get(pk=bk_idc_city_id)

        machine_type = machine["machine_type"]
        spec_id = machine.get("spec_id", 0)
        spec_config = machine.get("spec_config", {})

        Machine.objects.create(
            ip=ip,
            bk_host_id=inf.get("bk_host_id") or 0,
            bk_biz_id=machine["bk_biz_id"],
            access_layer=MachineTypeAccessLayerMap[machine_type],
            machine_type=machine_type,
            cluster_type=machine_type_to_cluster_type(machine_type),
            bk_city=bk_city_obj,
            bk_os_name=inf.get("bk_os_name") or "",
            bk_idc_area=inf.get("bk_idc_area") or "",
            bk_idc_area_id=inf.get("bk_idc_area_id") or 0,
            bk_sub_zone=inf.get("sub_zone") or "",
            bk_sub_zone_id=inf.get("sub_zone_id") or 0,
            bk_rack=inf.get("rack") or "",
            bk_rack_id=inf.get("rack_id") or 0,
            bk_svr_device_cls_name=inf.get("bk_svr_device_cls_name") or "",
            bk_idc_name=inf.get("idc_name") or "",
            bk_idc_id=inf.get("idc_id") or 0,
            bk_cloud_id=inf.get("bk_cloud_id") or 0,
            net_device_id=inf.get("net_device_id") or "",  # 这个 id 是个逗号分割的字符串
            spec_id=spec_id,
            spec_config=spec_config,
            creator=creator,
        )


@transaction.atomic
def delete(machines: Optional[List], bk_cloud_id: int):
    Machine.objects.filter(ip__in=machines, bk_cloud_id=bk_cloud_id).delete()


@transaction.atomic
def trans_module(bk_cloud_id: int, cluster_ids: Optional[List] = None, machines: Optional[List] = None, idle=False):

    machines_obj = Machine.objects.filter(ip__in=machines)

    if idle:
        machine_host_id_list = []
        for machine in machines_obj:
            machine_host_id_list.append(machine.bk_host_id)

        CCApi.transfer_host_to_recyclemodule({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_host_id": machine_host_id_list})
    else:
        # mysql主机转移模块、添加对应的服务实例
        transfer_host_in_cluster_module(
            cluster_ids=cluster_ids,
            ip_list=machines,
            machine_type=MachineType.BACKEND.value,
            bk_cloud_id=bk_cloud_id,
        )
