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
    """构造一个不带 DB 查询的云可用区索引"""
    index = apply_protocol.CloudZoneIndex.__new__(apply_protocol.CloudZoneIndex)
    index.region_by_zone = {
        "ap-nanjing-1": "ap-nanjing",
        "ap-nanjing-2": "ap-nanjing",
        "ap-nanjing-3": "ap-nanjing",
    }
    return index


@pytest.fixture
def zone_index():
    """把 CloudZoneIndex 换成不带 DB 查询的假索引"""
    with patch.object(apply_protocol, "CloudZoneIndex", return_value=build_index()):
        yield


def apply_params(
    location_spec,
    affinity=AffinityEnum.CROS_SUBZONE.value,
    current_hosts=None,
    count=2,
):
    return {
        "resource_type": "MySQL",
        "for_biz_id": 1,
        "details": [
            {
                "group_mark": "backend_0",
                "count": count,
                "affinity": affinity,
                "location_spec": location_spec,
                "current_hosts": current_hosts or [],
            }
        ],
    }


def test_v2_keeps_cloud_fields(zone_index):
    """云地域 + 云可用区原样下发，老字段一个都不出现"""
    params = apply_params({"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1", "ap-nanjing-2"]})
    payload = apply_protocol.build_v2_apply_params(params)

    detail = payload["details"][0]
    assert detail["location_spec"] == {
        "bk_cloud_region": "ap-nanjing",
        "bk_cloud_zone_list": ["ap-nanjing-1", "ap-nanjing-2"],
    }
    # 位置模式是请求级字段，不再放在 detail 里
    assert "affinity_dimension" not in detail
    assert payload["affinity_dimension"] == apply_protocol.CLOUD_ZONE_DIMENSION
    assert detail["affinity"] == AffinityEnum.CROS_SUBZONE.value


def test_v2_infers_region_from_zones(zone_index):
    """只给可用区时，地域由可用区推出来"""
    params = apply_params({"bk_cloud_zone_list": ["ap-nanjing-2"]}, affinity=AffinityEnum.NONE.value)
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["bk_cloud_region"] == "ap-nanjing"
    assert location_spec["bk_cloud_zone_list"] == ["ap-nanjing-2"]


def test_v2_random_region_keeps_cloud_zones(zone_index):
    """地域是 default（随机）但选了可用区：地域由可用区推出，可用区照常下发"""
    params = apply_params(
        {"bk_cloud_region": "default", "bk_cloud_zone_list": ["ap-nanjing-1"]}, affinity=AffinityEnum.NONE.value
    )
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["bk_cloud_region"] == "ap-nanjing"
    assert location_spec["bk_cloud_zone_list"] == ["ap-nanjing-1"]


def test_v2_keeps_region_when_zone_list_empty(zone_index):
    """跨可用区 + 随机（空列表）：只下发地域，可用区交给资源池决定"""
    params = apply_params({"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": []})
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["bk_cloud_region"] == "ap-nanjing"
    assert "bk_cloud_zone_list" not in location_spec


def test_v2_exclude_list_passthrough(zone_index):
    """排除可用区原样下发"""
    params = apply_params(
        {"bk_cloud_region": "ap-nanjing", "exclude_bk_cloud_zone_list": ["ap-nanjing-1"]},
        affinity=AffinityEnum.NONE.value,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1"]
    assert "bk_cloud_zone_list" not in location_spec


def test_v2_omits_location_spec_for_random_region(zone_index):
    """地域选「随机」且没有可用区时，整组不传 location_spec（不能塞 default）"""
    params = apply_params({"bk_cloud_region": "default", "bk_cloud_zone_list": []}, affinity=AffinityEnum.NONE.value)
    payload = apply_protocol.build_v2_apply_params(params)

    detail = payload["details"][0]
    assert "location_spec" not in detail
    assert "affinity_dimension" not in detail
    assert detail["affinity"] == AffinityEnum.NONE.value


def test_v2_keeps_detail_without_location_spec(zone_index):
    """指定主机申请没有位置条件，保持不出现 location_spec"""
    params = apply_params(None)
    payload = apply_protocol.build_v2_apply_params(params)

    assert "location_spec" not in payload["details"][0]


def test_v2_raises_when_cloud_zone_unresolvable(zone_index):
    """可用区不在登记表里直接报错，不能悄悄降级成「不限位置」"""
    params = apply_params({"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-9"]})

    with pytest.raises(apply_protocol.ResourceApplyException):
        apply_protocol.build_v2_apply_params(params)


def test_v2_rejects_legacy_city(zone_index):
    """城市口径已下线：还传 city 说明单据是改造前的格式，直接报错"""
    params = apply_params({"city": "南京", "bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1"]})

    with pytest.raises(apply_protocol.ResourceApplyException) as error:
        apply_protocol.build_v2_apply_params(params)
    assert "city" in str(error.value)


def test_v2_rejects_legacy_sub_zone_ids(zone_index):
    """园区 ID 不再反查，出现就报错"""
    params = apply_params({"bk_cloud_region": "ap-nanjing", "sub_zone_ids": ["1109"]})

    with pytest.raises(apply_protocol.ResourceApplyException) as error:
        apply_protocol.build_v2_apply_params(params)
    assert "sub_zone_ids" in str(error.value)


def test_v2_rejects_legacy_include_or_exclue(zone_index):
    """老的是否排除开关不再支持，避免排除语义被静默丢掉"""
    params = apply_params(
        {"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1"], "include_or_exclue": False}
    )

    with pytest.raises(apply_protocol.ResourceApplyException) as error:
        apply_protocol.build_v2_apply_params(params)
    assert "include_or_exclue" in str(error.value)


def test_v2_ignores_default_city_sentinel(zone_index):
    """存量单据里 city=default 表示随机，本身不表达约束，忽略即可"""
    params = apply_params(
        {"city": "default", "bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1"]},
        affinity=AffinityEnum.NONE.value,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec == {"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1"]}


def test_v2_keeps_current_hosts_cloud_zone(zone_index):
    """current_hosts 带 bk_cloud_zone 时原样保留"""
    params = apply_params(
        {"bk_cloud_region": "ap-nanjing"},
        affinity=AffinityEnum.SAME_SUBZONE.value,
        current_hosts=[{"ip": "1.1.1.1", "bk_host_id": 1, "bk_cloud_zone": "ap-nanjing-1", "rack_id": "rack-a"}],
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert payload["details"][0]["current_hosts"][0]["bk_cloud_zone"] == "ap-nanjing-1"


def test_v2_drops_current_hosts_without_zone(zone_index):
    """没有可用区的主机直接剔除，不再拿园区 ID 反查"""
    params = apply_params(
        {"bk_cloud_region": "ap-nanjing"},
        affinity=AffinityEnum.SAME_SUBZONE.value,
        current_hosts=[{"ip": "1.1.1.1", "bk_host_id": 1, "sub_zone_id": "1109", "rack_id": "rack-a"}],
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert payload["details"][0]["current_hosts"] == []


def _single_host_params(
    current_hosts,
    location_spec=None,
    affinity=AffinityEnum.CROS_SUBZONE.value,
    tolerance=None,
    count=1,
):
    """count 为 1 的扩容/加从库/替换/自愈场景"""
    detail = {
        "group_mark": "backend_0",
        "count": count,
        "affinity": affinity,
        "location_spec": location_spec if location_spec is not None else {"bk_cloud_region": "ap-nanjing"},
        "current_hosts": current_hosts,
    }
    if tolerance is not None:
        detail["tolerance"] = tolerance
    return {"resource_type": "MySQL", "for_biz_id": 1, "details": [detail]}


def _host(ip, zone, host_id):
    return {"ip": ip, "bk_host_id": host_id, "bk_cloud_zone": zone, "rack_id": f"rack-{zone}"}


def test_v2_count_one_cross_zone_excludes_occupied_zone(zone_index):
    """count=1 时服务端会把亲和性降级为 NONE，这里显式排除已有主机所在的可用区"""
    params = _single_host_params(current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1)])
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1"]
    assert location_spec["bk_cloud_region"] == "ap-nanjing"


def test_v2_count_one_cross_zone_keeps_include_when_other_zone_left(zone_index):
    """指定了 2 个可用区时，从包含列表里去掉已占用的那个，排除条件照旧下发"""
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1)],
        location_spec={"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1", "ap-nanjing-2"]},
    )
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["bk_cloud_zone_list"] == ["ap-nanjing-2"]
    assert location_spec["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1"]


def test_v2_count_one_cross_zone_no_extra_rule_when_already_spread(zone_index):
    """已有主机已分布在 2 个可用区、且都没到每区上限时，放哪都满足容灾，不加排除条件"""
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1), _host("1.1.1.2", "ap-nanjing-2", 2)]
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert "exclude_bk_cloud_zone_list" not in payload["details"][0]["location_spec"]


def test_v2_count_one_strong_affinity_excludes_all_occupied_zones(zone_index):
    """强亲和 3 节点替换 1 台：剩余 2 台在 A、B，新机器必须落到第三个可用区

    tolerance=0.33 时每区上限 ceil(3 * 0.33) = 1，A、B 都已满，两个区都要排除。
    """
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1), _host("1.1.1.2", "ap-nanjing-2", 2)],
        affinity=AffinityEnum.CROSS_SUBZONE_STRONG.value,
        tolerance=0.33,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert payload["details"][0]["location_spec"]["exclude_bk_cloud_zone_list"] == [
        "ap-nanjing-1",
        "ap-nanjing-2",
    ]


def test_v2_count_one_strong_affinity_keeps_include_when_third_zone_left(zone_index):
    """强亲和时包含列表里还剩第三个可用区：从包含列表去掉已占用的两个，不重复进排除列表"""
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1), _host("1.1.1.2", "ap-nanjing-2", 2)],
        location_spec={
            "bk_cloud_region": "ap-nanjing",
            "bk_cloud_zone_list": ["ap-nanjing-1", "ap-nanjing-2", "ap-nanjing-3"],
        },
        affinity=AffinityEnum.CROSS_SUBZONE_STRONG.value,
        tolerance=0.33,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec["bk_cloud_zone_list"] == ["ap-nanjing-3"]
    # 排除条件照旧下发，和收窄后的包含列表不冲突
    assert location_spec["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1", "ap-nanjing-2"]


def test_v2_count_one_strong_affinity_falls_back_when_include_all_occupied(zone_index):
    """勾选的可用区全被占满：放宽成「同地域内排除已占用区」，不能既包含又排除"""
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1), _host("1.1.1.2", "ap-nanjing-2", 2)],
        location_spec={"bk_cloud_region": "ap-nanjing", "bk_cloud_zone_list": ["ap-nanjing-1", "ap-nanjing-2"]},
        affinity=AffinityEnum.CROSS_SUBZONE_STRONG.value,
        tolerance=0.33,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert "bk_cloud_zone_list" not in location_spec
    assert location_spec["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1", "ap-nanjing-2"]
    assert location_spec["bk_cloud_region"] == "ap-nanjing"


def test_v2_count_one_strong_affinity_does_not_fix_impossible_case(zone_index):
    """强亲和只有 1 个可用区、只加 1 台：补不齐 3 个区，仍然尽力排除已占用的"""
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1)],
        affinity=AffinityEnum.CROSS_SUBZONE_STRONG.value,
        tolerance=0.33,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert payload["details"][0]["location_spec"]["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1"]


def test_v2_count_one_weak_affinity_excludes_zone_at_capacity(zone_index):
    """弱亲和 tolerance=0.5：A 已有 2 台达到 ceil(3 * 0.5) = 2 的上限，新机器只能去 B"""
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1), _host("1.1.1.2", "ap-nanjing-1", 2)],
        affinity=AffinityEnum.CROSS_SUBZONE_WEAK.value,
        tolerance=0.5,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert payload["details"][0]["location_spec"]["exclude_bk_cloud_zone_list"] == ["ap-nanjing-1"]


def test_v2_count_one_strong_affinity_skips_when_already_three_zones(zone_index):
    """强亲和已有 3 个可用区：上限 ceil(4 * 0.33) = 2 都没到，放哪都合规"""
    params = _single_host_params(
        current_hosts=[
            _host("1.1.1.1", "ap-nanjing-1", 1),
            _host("1.1.1.2", "ap-nanjing-2", 2),
            _host("1.1.1.3", "ap-nanjing-3", 3),
        ],
        affinity=AffinityEnum.CROSS_SUBZONE_STRONG.value,
        tolerance=0.33,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert "exclude_bk_cloud_zone_list" not in payload["details"][0]["location_spec"]


def test_v2_count_one_without_location_spec_only_warns(zone_index):
    """地域随机（没有 location_spec）时表达不了排除条件，只放行不改参数"""
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1), _host("1.1.1.2", "ap-nanjing-2", 2)],
        location_spec={"bk_cloud_region": "default", "bk_cloud_zone_list": []},
        affinity=AffinityEnum.CROSS_SUBZONE_STRONG.value,
        tolerance=0.33,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert "location_spec" not in payload["details"][0]


def test_v2_count_greater_than_one_keeps_affinity_untouched(zone_index):
    """count > 1 时服务端会正常计算亲和性，不补排除条件"""
    params = _single_host_params(
        current_hosts=[_host("1.1.1.1", "ap-nanjing-1", 1)],
        affinity=AffinityEnum.CROSS_SUBZONE_STRONG.value,
        tolerance=0.33,
        count=2,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert "exclude_bk_cloud_zone_list" not in payload["details"][0]["location_spec"]


@pytest.mark.parametrize(
    "total,tolerance,min_zones,affinity,expected",
    [
        (3, 0.33, 3, "CROSS_SUBZONE_STRONG", 1),  # 强亲和 3 节点：每区 1 台
        (4, 0.33, 3, "CROSS_SUBZONE_STRONG", 2),
        (3, 0.5, 2, "CROSS_SUBZONE_WEAK", 2),  # 弱亲和 3 节点：可以 2+1
        (5, 0.4, 2, "CROS_SUBZONE", 3),  # 跨可用区不吃 tolerance，按 2 个可用区均分
        (3, None, 2, "CROS_SUBZONE", 2),
        (2, 0, 2, "CROS_SUBZONE", 1),
        (0, 0.33, 3, "CROSS_SUBZONE_STRONG", 1),
    ],
)
def test_zone_capacity(total, tolerance, min_zones, affinity, expected):
    """每区上限与巡检 check_affinity_rules 的口径对齐"""
    assert apply_protocol._zone_capacity(total, tolerance, min_zones, affinity) == expected


def test_v2_count_one_cros_subzone_ignores_tolerance(zone_index):
    """跨可用区不看 tolerance：4 台分布在 A、B 各 2 台，加 1 台仍然满足 >= 2 个可用区

    tolerance=0.4 时若按比例算上限是 ceil(5 * 0.4) = 2，A、B 都会被排除；
    巡检对 CROS_SUBZONE 没有比例规则，按 2 个可用区均分上限是 ceil(5 / 2) = 3，不该干预。
    """
    params = _single_host_params(
        current_hosts=[
            _host("1.1.1.1", "ap-nanjing-1", 1),
            _host("1.1.1.2", "ap-nanjing-1", 2),
            _host("1.1.1.3", "ap-nanjing-2", 3),
            _host("1.1.1.4", "ap-nanjing-2", 4),
        ],
        affinity=AffinityEnum.CROS_SUBZONE.value,
        tolerance=0.4,
    )
    payload = apply_protocol.build_v2_apply_params(params)

    assert "exclude_bk_cloud_zone_list" not in payload["details"][0]["location_spec"]
