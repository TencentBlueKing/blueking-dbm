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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_meta.models.city_map import BKCity, BKSubzone, LogicalCity, resolve_cloud_region

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
    """可用区所属地域优先，且不受同城多个园区影响"""
    assert resolve_cloud_region(cloud_zones=["ap-nanjing-2"]) == "ap-nanjing"


def test_resolve_region_by_city(njnz_subzones):
    """跨机架/无 这类可用区为空时，用城市反查"""
    assert resolve_cloud_region(cloud_zones=[], city="测试-南京") == "ap-nanjing"


def test_resolve_region_ignores_default_city(njnz_subzones):
    """随机（default）不代表任何地域"""
    assert resolve_cloud_region(cloud_zones=[], city="default") == ""


def test_resolve_region_empty_when_unknown(njnz_subzones):
    """查不到就返回空串，由调用方决定是否留空"""
    assert resolve_cloud_region(cloud_zones=["ap-not-exist-1"], city="测试-不存在") == ""


def test_cluster_save_fills_cloud_region(njnz_subzones):
    """注册集群时按可用区补齐云地域，前端不需要额外传"""
    cluster = Cluster.objects.create(
        bk_biz_id=1,
        name="test-region-fill",
        immute_domain="test-region-fill.db",
        cluster_type=ClusterType.TenDBSingle.value,
        db_module_id=1,
        region="测试-南京",
        cloud_zone_list=["ap-nanjing-2"],
        creator="admin",
        updater="admin",
    )
    assert cluster.bk_cloud_region == "ap-nanjing"


def test_cluster_save_keeps_existing_cloud_region(njnz_subzones):
    """已有云地域的集群不被改写"""
    cluster = Cluster.objects.create(
        bk_biz_id=1,
        name="test-region-keep",
        immute_domain="test-region-keep.db",
        cluster_type=ClusterType.TenDBSingle.value,
        db_module_id=1,
        region="测试-南京",
        cloud_zone_list=["ap-nanjing-1"],
        bk_cloud_region="ap-manual",
        creator="admin",
        updater="admin",
    )
    assert cluster.bk_cloud_region == "ap-manual"
