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
from typing import Dict, List

import humanize
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.models import LogicalCity
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.infras.constants import InventoryTag

LCityModel = collections.namedtuple("LCityModel", ["city_code", "city_name", "inventory", "inventory_tag"])

HostSpecModel = collections.namedtuple("HostSpecModel", ["city_code", "type", "spec", "cpu", "mem", "description"])

CapSpecModel = collections.namedtuple(
    "CapSpecModel",
    [
        "cap_key",
        "total_memory",
        "maxmemory",
        "total_disk",
        "max_disk",
        "shard_num",
        "group_num",
        "selected",
    ],
)

host_specs = [
    HostSpecModel("nj", _("标准型SA2"), "SA2.SMALL4", _("1核"), "4GB", ""),
    HostSpecModel("sh", _("标准型S6"), "SA2.MEDIUM8", _("2核"), "8GB", ""),
    HostSpecModel("sh", _("标准型SA2"), "SA2.SMALL1", _("1核"), "1GB", ""),
    HostSpecModel("sz", _("标准型S5"), "S5.MEDIUM4", _("2核"), "4GB", ""),
    HostSpecModel("sh", "SA2.SMALL1", "S5t.SMALL1", _("1核"), "1GB", ""),
    HostSpecModel("sz", "S5t.SMALL4", "S5t.SMALL4", _("2核"), "4GB", ""),
]


def list_cities() -> List[LCityModel]:
    """返回逻辑城市列表"""
    # LogicalCity
    # TODO db_meta 中的 LogicalCity 现在只有一个 name 字段, 对应这里的 city_name, 用于前端展示
    # 但这里考虑用 city_code 来做传参 (取值是城市拼音或 id)
    # TODO 库存数量和标签待完善
    cities = []
    for city in LogicalCity.objects.all():
        city_code = city.name
        # 如果是default，则前端展示为无地域
        city_name = _("无地域") if city.name == "default" else city.name
        cities.append(LCityModel(city_code, city_name, "0", InventoryTag.SUFFICIENT.value))
    return cities


def list_host_specs() -> List[HostSpecModel]:
    # TODO 暂时全量返回，后续机型设计时再做考虑
    return [spec for spec in host_specs]


def list_cap_specs_cache(
    ip_source=IpSource.RESOURCE_POOL, cpu=None, mem=None, ssd_disk=None, group=None
) -> List[CapSpecModel]:
    """
    申请容量列表
    入参：单机型的cpu、内存；机器组数
    返回：可选择列表

    单机分片数：[cpu/2, cpu*2]、最好能被6整除
    1、2 ->  [1,4]
    3 ->  [2,6]
    4 ->  [2,8]
    8 ->  [4,16]
    16 -> [8,32]
    """

    # TODO: 结合资源池方案提供
    if ip_source == IpSource.RESOURCE_POOL:
        return []

    MAGIC_NUM = 6
    choices = []
    total_disk = ssd_disk * group
    total_mem = group * mem
    total_mem_display = humanize.naturalsize(total_mem * 1000 * 1000)
    min_shard_num = cpu / 2
    max_shard_num = cpu * 2

    # 如果cpu小于等于2，就每台机器部署2*cpu个实例
    if cpu <= 2:
        shard_num = max_shard_num
        choices.append(
            {
                "total_memory": total_mem_display,
                "shard_num": int(group * shard_num),
                "maxmemory": int(mem / shard_num),
                "group_num": group,
                "selected": True,
                "total_disk": total_disk,
                "max_disk": int(ssd_disk / shard_num),
            }
        )
    else:
        # 找到大于cpu/2，最小能被6整除的数
        shard_num = min_shard_num
        while shard_num % MAGIC_NUM:
            shard_num += 1

        index = 0
        while shard_num <= max_shard_num:
            if shard_num % MAGIC_NUM == 0:
                index += 1
                choices.append(
                    {
                        "total_memory": total_mem_display,
                        "shard_num": int(group * shard_num),
                        "maxmemory": int(mem / shard_num),
                        "group_num": group,
                        "selected": shard_num == cpu,
                        "total_disk": total_disk,
                        "max_disk": int(ssd_disk / shard_num),
                    }
                )
            shard_num += MAGIC_NUM

    # 补充复合key: <total_memory:maxmemory:shard_num:group_num>
    for c in choices:
        c["cap_key"] = "{total_memory}:{maxmemory}:{total_disk}:{max_disk}:{shard_num}:{group_num}".format(**c)
    return [CapSpecModel(**choice) for choice in choices]


def list_cap_specs_tendisplus(
    ip_source=IpSource.RESOURCE_POOL, cpu=None, mem=None, ssd_disk=None, group=None
) -> List[CapSpecModel]:
    """
    单机单实例
    至少需要3组机器，必须是奇数组
    """
    # TODO: 结合资源池方案提供
    if ip_source == IpSource.RESOURCE_POOL:
        return []

    choices = []
    total_disk = ssd_disk * group
    total_mem = group * mem
    total_mem_display = humanize.naturalsize(total_mem * 1000 * 1000 * 1000)
    choices.append(
        {
            "total_memory": total_mem_display,
            "shard_num": int(group),
            "maxmemory": int(mem),
            "group_num": group,
            "selected": True,
            "total_disk": total_disk,
            "max_disk": int(ssd_disk),
        }
    )

    for c in choices:
        c["cap_key"] = "{total_memory}:{maxmemory}:{total_disk}:{max_disk}:{shard_num}:{group_num}".format(**c)

    return [CapSpecModel(**choice) for choice in choices]


def list_cap_specs_ssd(
    ip_source=IpSource.RESOURCE_POOL, cpu=None, mem=None, ssd_disk=None, group=None
) -> List[CapSpecModel]:
    """
    申请容量列表
    入参：单机型的cpu、内存（MB）、ssd磁盘(GB)；机器组数
    返回：可选择列表

    机型：必须是SSD、大于16C
    单机分片数：[mem/6, mem/2]、最好能被6整除、不能超过cpu*2
    16c64g -> [12,18,24,30]
    """

    MAGIC_NUM = 6

    # TODO: 结合资源池方案提供
    if ip_source == IpSource.RESOURCE_POOL:
        return []

    # TODO: test only
    # if cpu < 16:
    #     return []
    # choices = []
    choices = [
        {
            "total_memory": "4 GB",
            "shard_num": 4,
            "maxmemory": 1024,
            "group_num": 1,
            "selected": True,
            "max_disk": 25,
            "total_disk": 100,
        }
    ]

    # MB -> GB
    mem = round(mem / 1024, 3)

    total_mem = group * mem
    total_mem_display = humanize.naturalsize(total_mem * 1000 * 1000 * 1000)
    total_disk = ssd_disk * group
    min_shard_num = round(mem / 6)
    max_shard_num = round(min(mem / 2, cpu * 2))

    # 找到大于mem/6，最小能被6整除的数
    shard_num = min_shard_num
    if shard_num % MAGIC_NUM:
        shard_num = shard_num + (MAGIC_NUM - shard_num % MAGIC_NUM)

    index = 0
    while shard_num <= max_shard_num:
        if shard_num % MAGIC_NUM == 0:
            index += 1
            choices.append(
                {
                    "total_memory": total_mem_display,
                    "shard_num": int(group * shard_num),
                    "maxmemory": int(mem / shard_num),
                    "group_num": group,
                    "selected": shard_num == cpu,
                    "total_disk": total_disk,
                    "max_disk": int(ssd_disk / shard_num),
                }
            )
        shard_num += MAGIC_NUM

    # 补充复合key: <total_memory:maxmemory:shard_num:group_num>
    for c in choices:
        c["cap_key"] = "{total_memory}:{maxmemory}:{total_disk}:{max_disk}:{shard_num}:{group_num}".format(**c)

    return [CapSpecModel(**choice) for choice in choices]


def get_city_code_name_map() -> Dict[str, str]:
    return {city.city_code: city.city_name for city in list_cities()}


def get_spec_display_map() -> Dict[str, str]:
    return {spec.spec: f"{spec.type}-{spec.cpu}-{spec.mem}" for spec in host_specs}
