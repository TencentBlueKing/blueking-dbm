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
import pytest

from backend.db_meta.models.city_map import (
    BKCity,
    BKSubzone,
    LogicalCity,
    is_unknown_cloud_region,
    resolve_cloud_region,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def njnz_subzones():
    """南京（逻辑城）下两个可用区、三个园区"""
    city = LogicalCity.objects.create(name="测试-南京")
    bk_city = BKCity.objects.create(bk_idc_city_id=99001, bk_idc_city_name="测试-南京", logical_city=city)
    for sub_zone, sub_zone_id, cloud_zone in [
        ("测试-江宁", 990011, "ap-nanjing-1"),
        ("测试-吉山", 990012, "ap-nanjing-1"),
        ("测试-浦口", 990013, "ap-nanjing-2"),
    ]:
        BKSubzone.objects.create(
            bk_sub_zone=sub_zone,
            bk_sub_zone_id=sub_zone_id,
            bk_city=bk_city,
            bk_cloud_region="ap-nanjing",
            bk_cloud_zone=cloud_zone,
        )
    return city, bk_city


def test_resolve_region_by_cloud_zone(njnz_subzones):
    """按可用区反查地域，不受同城多个园区影响"""
    assert resolve_cloud_region(cloud_zones=["ap-nanjing-2"]) == "ap-nanjing"


def test_resolve_region_empty_when_no_zone(njnz_subzones):
    """可用区随机/为空时推不出地域，返回空串"""
    assert resolve_cloud_region(cloud_zones=[]) == ""
    assert resolve_cloud_region() == ""


def test_resolve_region_empty_when_unknown(njnz_subzones):
    """可用区没登记时返回空串，由调用方决定是否留空"""
    assert resolve_cloud_region(cloud_zones=["ap-not-exist-1"]) == ""


def test_is_unknown_cloud_region():
    """空值和「随机」哨兵值都算没有真实地域，不能被当成真实地域下发"""
    assert is_unknown_cloud_region("") is True
    assert is_unknown_cloud_region(None) is True
    assert is_unknown_cloud_region("   ") is True
    assert is_unknown_cloud_region("default") is True
    assert is_unknown_cloud_region(" ap-nanjing ") is False
