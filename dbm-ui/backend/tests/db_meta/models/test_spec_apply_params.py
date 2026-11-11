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
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.configuration.constants import AffinityEnum
from backend.db_meta.models.spec import Spec
from backend.db_services.dbresource import apply_protocol


class FakeZoneIndex:
    """只实现协议层用到的索引，避免测试查库"""

    region_by_zone = {"ap-guangzhou-3": "ap-guangzhou"}


def build_spec():
    """构造只用于跑通 _get_apply_params_detail 的假 Spec 实例"""
    return SimpleNamespace(
        storage_spec=[{"mount_point": "/data", "type": "ALL", "min": 100, "max": 200}],
        device_class=["S5.MEDIUM4"],
        cpu=None,
        mem=None,
    )


def build_detail(location_spec, affinity=AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value):
    return Spec._get_apply_params_detail(
        build_spec(),
        group_mark="0_bk_new_orphan_0",
        count=1,
        bk_cloud_id=0,
        affinity=affinity,
        location_spec=location_spec,
    )


@pytest.mark.django_db
def test_cloud_fields_are_kept():
    """云地域 + 云可用区原样透传，可用区统一成字符串"""
    detail = build_detail({"bk_cloud_region": "ap-guangzhou", "bk_cloud_zone_list": ["ap-guangzhou-3"]})

    location_spec = detail["location_spec"]
    assert location_spec["bk_cloud_region"] == "ap-guangzhou"
    assert location_spec["bk_cloud_zone_list"] == ["ap-guangzhou-3"]


@pytest.mark.django_db
def test_region_only_is_kept():
    """只有云地域、没有可用区时同样要保留"""
    detail = build_detail({"bk_cloud_region": "ap-guangzhou"})

    assert detail["location_spec"] == {"bk_cloud_region": "ap-guangzhou"}


@pytest.mark.django_db
def test_exclude_list_is_kept():
    """排除列表也是位置条件，不能被当成「没有约束」丢掉"""
    detail = build_detail({"exclude_bk_cloud_zone_list": ["ap-guangzhou-3"]})

    assert detail["location_spec"]["exclude_bk_cloud_zone_list"] == ["ap-guangzhou-3"]


@pytest.mark.django_db
def test_random_region_without_zones_omits_location_spec():
    """双随机（地域 default + 未选可用区）下发到 v2 时整组不带位置条件"""
    detail = build_detail({"bk_cloud_region": "default"}, affinity=AffinityEnum.NONE.value)
    params = {"for_biz_id": 4, "resource_type": "mysql", "details": [detail]}

    with patch.object(apply_protocol, "CloudZoneIndex", return_value=FakeZoneIndex()):
        payload = apply_protocol.build_v2_apply_params(params)

    assert "location_spec" not in payload["details"][0]


@pytest.mark.django_db
def test_legacy_fields_are_not_dropped():
    """园区口径的老字段不能被静默丢掉，要留给申请层报错"""
    detail = build_detail({"city": "广州", "sub_zone_ids": ["1109"]})

    assert detail["location_spec"] == {"city": "广州", "sub_zone_ids": ["1109"]}


@pytest.mark.django_db
def test_legacy_location_spec_raises_on_apply():
    """老单据（只有城市 + 园区）在申请层直接报错，而不是悄悄变成「不限位置」"""
    detail = build_detail({"city": "广州", "sub_zone_ids": ["1109"]})
    params = {"for_biz_id": 4, "resource_type": "mysql", "details": [detail]}

    with patch.object(apply_protocol, "CloudZoneIndex", return_value=FakeZoneIndex()):
        with pytest.raises(apply_protocol.ResourceApplyException):
            apply_protocol.build_v2_apply_params(params)


@pytest.mark.django_db
def test_default_region_cluster_sends_location_to_v2():
    """集群 region=default 但记录了可用区，v2 必须带上地域 + 可用区"""
    detail = build_detail({"bk_cloud_region": "ap-guangzhou", "bk_cloud_zone_list": ["ap-guangzhou-3"]})
    params = {"for_biz_id": 4, "resource_type": "mysql", "details": [detail]}

    with patch.object(apply_protocol, "CloudZoneIndex", return_value=FakeZoneIndex()):
        payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec == {"bk_cloud_region": "ap-guangzhou", "bk_cloud_zone_list": ["ap-guangzhou-3"]}
    # affinity_dimension 是请求级字段，不再写在单个 detail 里
    assert payload["affinity_dimension"] == apply_protocol.CLOUD_ZONE_DIMENSION
