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
    """只实现协议层用到的两个方法，避免测试查库"""

    zone_by_subzone_id = {"1201": "ap-guangzhou-3"}

    def resolve_zone(self, value):
        return str(value).strip() if value else ""


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
def test_default_city_keeps_cloud_zone():
    """地域随机但集群记录了可用区时，只清 city，保留可用区与地域"""
    detail = build_detail({"city": "default", "sub_zone_ids": ["ap-guangzhou-3"], "bk_cloud_region": "ap-guangzhou"})

    location_spec = detail["location_spec"]
    assert location_spec is not None
    assert location_spec["city"] == ""
    assert location_spec["sub_zone_ids"] == ["ap-guangzhou-3"]
    assert location_spec["bk_cloud_region"] == "ap-guangzhou"


@pytest.mark.django_db
def test_default_city_keeps_region_only():
    """只有云地域、没有可用区时同样要保留"""
    detail = build_detail({"city": "default", "sub_zone_ids": [], "bk_cloud_region": "ap-guangzhou"})

    assert detail["location_spec"]["city"] == ""
    assert detail["location_spec"]["bk_cloud_region"] == "ap-guangzhou"


@pytest.mark.django_db
def test_default_city_keeps_exclude_list():
    """排除列表也是位置条件，不能因为 city 是 default 就丢掉"""
    detail = build_detail({"city": "default", "exclude_sub_zone_ids": ["1109"]})

    assert detail["location_spec"] is not None
    assert detail["location_spec"]["exclude_sub_zone_ids"] == ["1109"]


@pytest.mark.django_db
def test_default_city_without_location_is_none():
    """双随机（地域随机 + 未选可用区）保持原行为：整组无位置条件"""
    detail = build_detail({"city": "default", "sub_zone_ids": []})

    assert detail["location_spec"] is None


@pytest.mark.django_db
def test_regular_city_is_untouched():
    """正常城市不受影响"""
    detail = build_detail({"city": "广州", "sub_zone_ids": ["ap-guangzhou-3"]})

    assert detail["location_spec"]["city"] == "广州"
    assert detail["location_spec"]["sub_zone_ids"] == ["ap-guangzhou-3"]


@pytest.mark.django_db
def test_missing_city_does_not_raise():
    """location_spec 缺 city 时不能 KeyError（老前端可能省略该字段）"""
    detail = build_detail({"sub_zone_ids": ["ap-guangzhou-3"]})

    assert detail["location_spec"]["sub_zone_ids"] == ["ap-guangzhou-3"]


@pytest.mark.django_db
def test_default_region_cluster_sends_location_to_v2():
    """复现生产问题：集群 region=default 但记录了可用区，v2 必须带上 location_spec"""
    detail = build_detail({"city": "default", "sub_zone_ids": ["ap-guangzhou-3"], "bk_cloud_region": "ap-guangzhou"})
    params = {"for_biz_id": 4, "resource_type": "mysql", "details": [detail]}

    with patch.object(apply_protocol, "CloudZoneIndex", return_value=FakeZoneIndex()):
        payload = apply_protocol.build_v2_apply_params(params)

    location_spec = payload["details"][0]["location_spec"]
    assert location_spec == {"bk_cloud_region": "ap-guangzhou", "bk_cloud_zone_list": ["ap-guangzhou-3"]}
    # affinity_dimension 是请求级字段，不再写在单个 detail 里
    assert payload["affinity_dimension"] == apply_protocol.CLOUD_ZONE_DIMENSION
