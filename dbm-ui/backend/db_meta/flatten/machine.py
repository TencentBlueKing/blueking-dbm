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
from typing import Dict, List

from django.db.models import QuerySet

from backend.db_meta.models import Machine

logger = logging.getLogger("root")


def _machine_prefetch() -> List:
    return [
        "machine",
        "machine__bk_city",
        "machine__bk_city__logical_city",
    ]


def _single_machine_info(mobj: Machine) -> Dict:
    return {
        **__single_machine_base_info(mobj),
        **_single_machine_city_info(mobj),
        **_single_machine_cc_info(mobj),
    }


def __single_machine_base_info(mobj: Machine) -> Dict:
    return {
        "ip": mobj.ip,
        "bk_biz_id": mobj.bk_biz_id,
        "machine_type": mobj.machine_type,
        "cluster_type": mobj.cluster_type,
        "access_layer": mobj.access_layer,
        "db_module_id": mobj.db_module_id,
    }


def _single_machine_city_info(mobj: Machine) -> Dict:
    return {
        "bk_idc_city_id": mobj.bk_city.bk_idc_city_id,
        "bk_idc_city_name": mobj.bk_city.bk_idc_city_name,
        "logical_city_id": mobj.bk_city.logical_city.id,
        "logical_city_name": mobj.bk_city.logical_city.name,
    }


def _single_machine_cc_info(mobj: Machine) -> Dict:
    return {
        "bk_os_name": mobj.bk_os_name,
        "bk_idc_area": mobj.bk_idc_area,
        "bk_idc_area_id": mobj.bk_idc_area_id,
        "bk_sub_zone": mobj.bk_sub_zone,
        "bk_sub_zone_id": mobj.bk_sub_zone_id,
        "bk_rack": mobj.bk_rack,
        "bk_rack_id": mobj.bk_rack_id,
        "bk_svr_device_cls_name": mobj.bk_svr_device_cls_name,
        "bk_idc_name": mobj.bk_idc_name,
        "bk_idc_id": mobj.bk_idc_id,
        "bk_cloud_id": mobj.bk_cloud_id,
        "net_device_id": mobj.net_device_id,
    }


def machine(machines: QuerySet) -> List[Dict]:
    machine_list = list(
        machines.prefetch_related(
            "bk_city",
            "bk_city__logical_city",
        )
    )
    res = []
    for m in machine_list:
        info = {**_single_machine_info(m)}

        res.append(info)

    return res
