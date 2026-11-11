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
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.models import BKCity, LogicalCity
from backend.db_meta.models.city_map import BKSubzone
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
    for city in LogicalCity.objects.all().order_by("-name"):
        city_code = city.name
        # 如果是default，则前端展示为无地域
        city_name = _("随机") if city.name == "default" else city.name
        cities.append(LCityModel(city_code, city_name, "0", InventoryTag.SUFFICIENT.value))
    return cities


def list_common_cities():
    """返回常用城市列表"""
    cities = []
    common_cities_map = {}
    commit_city_list = SystemSettings.get_setting_value(
        key=SystemSettingsEnum.COMMON_CITIES.value,
        default=[],
    )
    for city in LogicalCity.objects.all().order_by("-name"):
        city_code = city.name
        # 如果是default，则前端展示为无地域
        city_name = _("随机") if city.name == "default" else city.name
        if city_code in commit_city_list:
            common_cities_map[city_code] = LCityModel(city_code, city_name, "0", InventoryTag.SUFFICIENT.value)
        else:
            cities.append(LCityModel(city_code, city_name, "0", InventoryTag.SUFFICIENT.value))
    common_cities = [
        common_cities_map[city_name] for city_name in commit_city_list if common_cities_map.get(city_name)
    ]
    return cities, common_cities


def list_logic_cities() -> List:
    """返回逻辑城市的映射关系"""
    cities = BKCity.objects.all().order_by("bk_idc_city_name")
    logic_cities = []
    for city in cities:
        logic_cities.append({**model_to_dict(city), "logical_city_name": city.logical_city.name})
    return logic_cities


def list_subzones(city_code: str = "") -> List:
    subzones = BKSubzone.objects.select_related("bk_city").all()
    if city_code:
        subzones = subzones.filter(bk_city__bk_idc_city_name=city_code)

    subzone_infos = []
    for zone in subzones:
        subzone_infos.append({**model_to_dict(zone), "bk_city_code": zone.bk_city.bk_idc_city_name})
    return subzone_infos


def list_cloud_zones(city_code: str = "", region: str = "") -> List:
    """查询云可用区，并把每个可用区下登记过的园区一起带出去

    部署页的可用区卡片要展示「这个可用区包含哪些园区」，列的是该可用区下
    登记过的全部园区（不管现在有没有机器），园区用全称，如「南京-江宁」。
    """
    qs = BKSubzone.objects.select_related("bk_city").exclude(bk_cloud_zone__isnull=True).exclude(bk_cloud_zone="")
    if city_code:
        qs = qs.filter(bk_city__bk_idc_city_name=city_code)
    if region:
        qs = qs.filter(bk_cloud_region=region)

    cloud_zone_map: Dict[str, Dict] = {}
    for subzone in qs.order_by("bk_cloud_zone", "bk_city__bk_idc_city_name", "bk_sub_zone"):
        city_name = subzone.bk_city.bk_idc_city_name if subzone.bk_city else ""
        sub_zone_name = subzone.bk_sub_zone or ""
        # 园区全称自带城市前缀，如「南京-江宁」
        if sub_zone_name.startswith(city_name):
            full_name = sub_zone_name
        else:
            full_name = f"{city_name}-{sub_zone_name}".strip("-")
        info = cloud_zone_map.setdefault(
            subzone.bk_cloud_zone,
            {
                "bk_cloud_zone": subzone.bk_cloud_zone,
                "bk_cloud_region": subzone.bk_cloud_region or "",
                "sub_zones": [],
            },
        )
        if full_name and full_name not in info["sub_zones"]:
            info["sub_zones"].append(full_name)

    return [cloud_zone_map[zone] for zone in sorted(cloud_zone_map)]


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
