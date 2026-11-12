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


def test_v1_passthrough():
    """默认走 v1，请求体一个字节都不改"""
    params = apply_params({"city": "南京", "sub_zone_ids": ["1109"]})
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v1"):
        version, payload = apply_protocol.build_apply_request(params)
    assert version == apply_protocol.API_VERSION_V1
    assert payload is params


def test_v1_expands_cloud_zone_to_subzone_ids(zone_index):
    """v1 只认园区 ID，可用区要反向展开；缺 city 时用可用区反查逻辑城"""
    params = apply_params({"sub_zone_ids": ["ap-nanjing-1"]})
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v1"):
        payload = apply_protocol.build_v1_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["sub_zone_ids"] == ["1109", "1110"]
    assert location_spec["city"] == "南京"


def test_v1_keeps_unknown_zone_value(zone_index):
    """可用区展开不出来时保留原值，让 v1 照旧报资源不足，不要悄悄放宽条件"""
    params = apply_params({"city": "南京", "sub_zone_ids": ["ap-unknown-9"]})
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v1"):
        payload = apply_protocol.build_v1_apply_params(params)

    assert payload["details"][0]["location_spec"]["sub_zone_ids"] == ["ap-unknown-9"]


def test_v2_converts_subzone_id_to_cloud_zone(zone_index):
    """园区 ID 反查成可用区，地域从可用区推出来"""
    params = apply_params({"city": "南京", "sub_zone_ids": ["1109", "1111"]})
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v2"):
        payload = apply_protocol.build_v2_apply_params(params)

    detail = payload["details"][0]
    assert detail["location_spec"]["bk_cloud_zone_list"] == ["ap-nanjing-1", "ap-nanjing-2"]
    assert detail["location_spec"]["bk_cloud_region"] == "ap-nanjing"
    # v1 的位置字段不能带到 v2
    assert "city" not in detail["location_spec"]
    assert "sub_zone_ids" not in detail["location_spec"]
    assert detail["affinity_dimension"] == apply_protocol.CLOUD_ZONE_DIMENSION
    assert detail["affinity"] == AffinityEnum.CROS_SUBZONE.value


def test_v2_random_fills_two_zones(zone_index):
    """跨可用区 + 随机（空列表）时，在所选地域内补两个可用区"""
    params = apply_params({"city": "南京", "sub_zone_ids": []})
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v2"):
        payload = apply_protocol.build_v2_apply_params(params)

    zones = payload["details"][0]["location_spec"]["bk_cloud_zone_list"]
    assert sorted(zones) == ["ap-nanjing-1", "ap-nanjing-2"]


def test_v2_exclude_mode_uses_exclude_field(zone_index):
    """include_or_exclue=False 要转成 exclude_bk_cloud_zone_list"""
    params = apply_params({"city": "南京", "sub_zone_ids": ["1109"], "include_or_exclue": False})
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v2"):
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
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v2"):
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
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v2"):
        payload = apply_protocol.build_v2_apply_params(params)

    assert payload["details"][0]["current_hosts"] == []


def test_v2_keeps_detail_without_location_spec(zone_index):
    """指定主机申请没有位置条件，保持不出现 location_spec"""
    params = apply_params(None)
    with patch.object(apply_protocol.env, "RESOURCE_APPLY_API_VERSION", "v2"):
        payload = apply_protocol.build_v2_apply_params(params)

    detail = payload["details"][0]
    assert "location_spec" not in detail
    assert "affinity_dimension" not in detail
