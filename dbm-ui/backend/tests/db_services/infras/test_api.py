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
from rest_framework.test import APIRequestFactory, force_authenticate

from backend.db_meta.models import BKCity
from backend.db_meta.models.city_map import BKSubzone
from backend.db_services.infras.views import HostSpecViewSet, LogicalCityViewSet

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


def test_list_cities(bk_user):
    request = factory.get(
        "/apis/infras/cities/",
    )
    force_authenticate(request, user=bk_user)
    view = LogicalCityViewSet.as_view({"get": "list_cities"})
    response = view(request)
    data = response.data
    assert len(data) > 0


def test_list_host_specs(bk_user):
    request = factory.get(
        "/apis/infras/cities/sh/host_specs/",
    )
    force_authenticate(request, user=bk_user)
    view = HostSpecViewSet.as_view({"get": "list_host_specs"})
    response = view(request)
    data = response.data
    assert len(data) == 6
    assert data[0]["spec"] == "SA2.SMALL4"


def test_list_cloud_regions(bk_user):
    """全量地域：只返回真实地域，不返回 default（随机由前端写死）"""
    request = factory.get("/apis/infras/cities/list_cloud_regions/")
    force_authenticate(request, user=bk_user)
    view = LogicalCityViewSet.as_view({"get": "list_cloud_regions"})
    response = view(request)

    assert response.status_code == 200
    regions = [item["bk_cloud_region"] for item in response.data]
    assert "default" not in regions
    for item in response.data:
        assert "display_name" in item
        assert "inventory_tag" in item


def test_list_cloud_regions_reads_subzones(bk_user):
    """地域列表来自 BKSubzone 登记的云地域，并带上该地域的可用区个数"""
    bk_city = BKCity.objects.first()
    BKSubzone.objects.create(
        bk_sub_zone="测试-江宁",
        bk_sub_zone_id=880001,
        bk_city=bk_city,
        bk_cloud_region="ap-nanjing",
        bk_cloud_zone="ap-nanjing-1",
    )
    BKSubzone.objects.create(
        bk_sub_zone="测试-吉山",
        bk_sub_zone_id=880002,
        bk_city=bk_city,
        bk_cloud_region="ap-nanjing",
        bk_cloud_zone="ap-nanjing-2",
    )

    request = factory.get("/apis/infras/cities/list_cloud_regions/")
    force_authenticate(request, user=bk_user)
    view = LogicalCityViewSet.as_view({"get": "list_cloud_regions"})
    response = view(request)

    region_map = {item["bk_cloud_region"]: item for item in response.data}
    assert "ap-nanjing" in region_map
    # 跨可用区要求地域下至少 2 个可用区，前端据此过滤地域下拉
    assert region_map["ap-nanjing"]["zone_count"] == 2


def test_list_common_cloud_regions(bk_user):
    """常用 / 非常用分组，两个 key 都要有"""
    request = factory.get("/apis/infras/cities/list_common_cloud_regions/")
    force_authenticate(request, user=bk_user)
    view = LogicalCityViewSet.as_view({"get": "list_common_cloud_regions"})
    response = view(request)

    assert response.status_code == 200
    assert "common" in response.data
    assert "uncommon" in response.data
