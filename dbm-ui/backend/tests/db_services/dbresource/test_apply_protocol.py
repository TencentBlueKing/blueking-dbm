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
from unittest.mock import patch

import pytest

from backend.configuration.constants import AffinityEnum
from backend.db_services.dbresource import apply_protocol


def build_index():
    """构造一个不带 DB 查询的园区/可用区索引"""
    index = apply_protocol.CloudZoneIndex.__new__(apply_protocol.CloudZoneIndex)
    index.zone_by_subzone_id = {"1109": "ap-nanjing-1", "1110": "ap-nanjing-1", "1111": "ap-nanjing-2"}
    index.region_by_subzone_id = {"1109": "ap-nanjing", "1110": "ap-nanjing", "1111": "ap-nanjing"}
    index.zone_by_subzone_name = {"江宁": "ap-nanjing-1", "吉山": "ap-nanjing-2"}
    index.region_by_zone = {"ap-nanjing-1": "ap-nanjing", "ap-nanjing-2": "ap-nanjing"}
    index.zones_by_city = {"南京": {"ap-nanjing-1", "ap-nanjing-2"}}
    index.subzone_ids_by_zone = {"ap-nanjing-1": ["1109", "1110"], "ap-nanjing-2": ["1111"]}
    index.city_by_zone = {"ap-nanjing-1": "南京", "ap-nanjing-2": "南京"}
    return index


@pytest.fixture
def zone_index():
    """把 CloudZoneIndex 换成不带 DB 查询的假索引"""
    with patch.object(apply_protocol, "CloudZoneIndex", return_value=build_index()):
        yield


def apply_params(location_spec, affinity=AffinityEnum.CROS_SUBZONE.value, current_hosts=None):
    return {
        "resource_type": "MySQL",
        "for_biz_id": 1,
        "details": [
            {
                "group_mark": "backend_0",
                "count": 2,
                "affinity": affinity,
                "location_spec": location_spec,
                "current_hosts": current_hosts or [],
            }
        ],
    }


def test_v2_converts_subzone_id_to_cloud_zone(zone_index):
    """园区 ID 反查成可用区，地域从可用区推出来"""
    params = apply_params({"city": "南京", "sub_zone_ids": ["1109", "1111"]})
    payload = apply_protocol.build_v2_apply_params(params)

    detail = payload["details"][0]
    assert detail["location_spec"]["bk_cloud_zone_list"] == ["ap-nanjing-1", "ap-nanjing-2"]
    assert detail["location_spec"]["bk_cloud_region"] == "ap-nanjing"
    # 老位置字段不能带到 v2
    assert "city" not in detail["location_spec"]
    assert "sub_zone_ids" not in detail["location_spec"]
    assert detail["affinity_dimension"] == apply_protocol.CLOUD_ZONE_DIMENSION
    assert detail["affinity"] == AffinityEnum.CROS_SUBZONE.value


def test_v2_keeps_empty_zone_list_as_random(zone_index):
    """跨可用区 + 随机（空列表）：不预选可用区，交给资源池在地域内决定"""
    params = apply_params({"city": "南京", "sub_zone_ids": []})
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["bk_cloud_region"] == "ap-nanjing"
    assert "bk_cloud_zone_list" not in location_spec


def test_v2_exclude_mode_uses_exclude_field(zone_index):
    """include_or_exclue=False 要转成 exclude_bk_cloud_zone_list"""
    params = apply_params({"city": "南京", "sub_zone_ids": ["1109"], "include_or_exclue": False})
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1"]
    assert "bk_cloud_zone_list" not in location_spec


def test_v2_fills_current_hosts_cloud_zone(zone_index):
    """current_hosts 只有 sub_zone_id 时补出 bk_cloud_zone"""
    params = apply_params(
        {"city": "南京", "sub_zone_ids": []},
        affinity=AffinityEnum.SAME_SUBZONE.value,
        current_hosts=[{"ip": "1.1.1.1", "bk_host_id": 1, "sub_zone_id": "1109", "rack_id": "rack-a"}],
    )
    payload = apply_protocol.build_v2_apply_params(params)

    host = payload["details"][0]["current_hosts"][0]
    assert host["bk_cloud_zone"] == "ap-nanjing-1"


def test_v2_drops_current_hosts_without_zone(zone_index):
    """补不出可用区的主机从 current_hosts 里剔除，避免整单被服务端拒绝"""
    params = apply_params(
        {"city": "南京", "sub_zone_ids": []},
        affinity=AffinityEnum.SAME_SUBZONE.value,
        current_hosts=[{"ip": "1.1.1.1", "bk_host_id": 1, "sub_zone_id": "9999", "rack_id": "rack-a"}],
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert payload["details"][0]["current_hosts"] == []


def test_v2_omits_location_spec_for_random_region(zone_index):
    """地域选「无限制/随机」且没有可用区时，整组不传 location_spec（不能塞 default）"""
    params = apply_params({"city": "default", "sub_zone_ids": []}, affinity=AffinityEnum.NONE.value)
    payload = apply_protocol.build_v2_apply_params(params)

    detail = payload["details"][0]
    assert "location_spec" not in detail
    assert "affinity_dimension" not in detail
    assert detail["affinity"] == AffinityEnum.NONE.value


def test_v2_keeps_detail_without_location_spec(zone_index):
    """指定主机申请没有位置条件，保持不出现 location_spec"""
    params = apply_params(None)
    payload = apply_protocol.build_v2_apply_params(params)

    detail = payload["details"][0]
    assert "location_spec" not in detail
    assert "affinity_dimension" not in detail


def test_v2_accepts_bk_cloud_zone_list_directly(zone_index):
    """新协议直接给 bk_cloud_zone_list，不再走 sub_zone_ids"""
    params = apply_params({"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1"]})
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec == {"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1"]}


def test_v2_default_region_keeps_cloud_zones(zone_index):
    """地域是 default（随机）但选了可用区：地域由可用区推出，可用区照常下发"""
    params = apply_params({"bk_cloud_region": "default", "sub_zone_ids": ["1109"]})
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["bk_cloud_region"] == "ap-nanjing"
    assert location_spec["bk_cloud_zone_list"] == ["ap-nanjing-1"]


def _single_host_params(current_hosts, location_spec=None, affinity=AffinityEnum.CROS_SUBZONE.value):
    """count=1 的扩容/加从库场景"""
    return {
        "resource_type": "MySQL",
        "for_biz_id": 1,
        "details": [
            {
                "group_mark": "backend_0",
                "count": 1,
                "affinity": affinity,
                "location_spec": location_spec if location_spec is not None else {"city": "南京", "sub_zone_ids": []},
                "current_hosts": current_hosts,
            }
        ],
    }


def test_v2_count_one_cross_zone_excludes_occupied_zone(zone_index):
    """count=1 时服务端会把亲和性降级为 NONE，这里显式排除已有主机所在的可用区"""
    params = _single_host_params(
        current_hosts=[{"ip": "1.1.1.1", "bk_host_id": 1, "bk_cloud_zone": "ap-nanjing-1", "rack_id": "rack-a"}]
    )
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1"]
    assert location_spec["bk_cloud_region"] == "ap-nanjing"


def test_v2_count_one_cross_zone_keeps_include_when_other_zone_left(zone_index):
    """指定了 2 个可用区时，从包含列表里去掉已占用的那个，不再重复出现在排除列表里互相冲突"""
    params = _single_host_params(
        current_hosts=[{"ip": "1.1.1.1", "bk_host_id": 1, "bk_cloud_zone": "ap-nanjing-1", "rack_id": "rack-a"}],
        location_spec={"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1", "ap-nanjing-2"]},
    )
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["bk_cloud_zone_list"] == ["ap-nanjing-2"]
    assert location_spec["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1"]


def test_v2_count_one_cross_zone_no_extra_rule_when_already_spread(zone_index):
    """已有主机已分布在 2 个可用区时，新增 1 台放哪都满足容灾，不加排除条件"""
    params = _single_host_params(
        current_hosts=[
            {"ip": "1.1.1.1", "bk_host_id": 1, "bk_cloud_zone": "ap-nanjing-1", "rack_id": "rack-a"},
            {"ip": "1.1.1.2", "bk_host_id": 2, "bk_cloud_zone": "ap-nanjing-2", "rack_id": "rack-b"},
        ]
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert "exclude_bk_cloud_zone_list" not in payload["details"][0]["location_spec"]


def test_v2_raises_when_cloud_zone_unresolvable(zone_index):
    """位置解析不出来时直接报错，不能悄悄降级成「不限位置」"""
    params = apply_params({"city": "南京", "sub_zone_ids": ["9999"]})

    with pytest.raises(apply_protocol.ResourceApplyException):
        apply_protocol.build_v2_apply_params(params)
