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

from backend.db_meta.models import BKCity
from backend.db_meta.models.city_map import BKSubzone
from backend.db_services.dbresource.apply_protocol import normalize_location_zones
from backend.ticket.builders.common.base import get_location_zones
from backend.ticket.exceptions import TicketParamsVerifyException

pytestmark = pytest.mark.django_db


@pytest.fixture
def subzones():
    """两个同可用区园区 + 一个不同可用区园区"""
    bk_city = BKCity.objects.first()
    for sub_zone, sub_zone_id, cloud_zone, region in [
        ("测试-江宁", 990021, "ap-nanjing-1", "ap-nanjing"),
        ("测试-吉山", 990022, "ap-nanjing-1", "ap-nanjing"),
        ("测试-浦口", 990023, "ap-nanjing-2", "ap-nanjing"),
    ]:
        BKSubzone.objects.create(
            bk_sub_zone=sub_zone,
            bk_sub_zone_id=sub_zone_id,
            bk_city=bk_city,
            bk_cloud_region=region,
            bk_cloud_zone=cloud_zone,
        )


def test_legacy_sub_zone_ids_are_ignored(subzones):
    """园区口径已下线：sub_zone_ids 不再反查，取不到可用区"""
    assert get_location_zones({"sub_zone_ids": [990021, 990023]}) == []


def test_duplicate_zones_are_deduped(subzones):
    """同一个可用区重复传入时归一后要去重"""
    assert get_location_zones({"bk_cloud_zone_list": ["ap-nanjing-1", "ap-nanjing-1"]}) == ["ap-nanjing-1"]


def test_cloud_zone_list_passes_through(subzones):
    """新协议直接传可用区，原样返回"""
    assert get_location_zones({"bk_cloud_zone_list": ["ap-nanjing-1"]}) == ["ap-nanjing-1"]


def test_cloud_zone_list_has_priority(subzones):
    """两个 key 同时存在时以新字段为准"""
    assert get_location_zones({"bk_cloud_zone_list": ["ap-nanjing-2"], "sub_zone_ids": [990021]}) == ["ap-nanjing-2"]


def test_unknown_cloud_zone_raises(subzones):
    """没登记过的可用区直接拒单，不允许把脏值写进新字段"""
    with pytest.raises(TicketParamsVerifyException):
        get_location_zones({"bk_cloud_zone_list": ["ap-nanjing-9"]})


def test_empty_location_spec_returns_empty(subzones):
    assert get_location_zones({}) == []
    assert get_location_zones(None) == []


def test_zone_name_is_kept(subzones):
    """已经是可用区名时直接保留"""
    assert normalize_location_zones({"bk_cloud_zone_list": ["ap-nanjing-2"]}) == ["ap-nanjing-2"]
