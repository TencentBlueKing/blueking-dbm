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
from unittest.mock import MagicMock, patch

import pytest

from backend.db_services.dbbase.constants import IpSource
from backend.db_services.infras import host

pytestmark = pytest.mark.django_db


class TestHostFunctions:
    """测试 host 模块函数"""

    @patch("backend.db_services.infras.host.LogicalCity.objects.all")
    def test_list_cities(self, mock_cities):
        """测试列出城市"""
        mock_city1 = MagicMock()
        mock_city1.name = "shanghai"
        mock_city2 = MagicMock()
        mock_city2.name = "default"

        mock_cities.return_value.order_by.return_value = [mock_city1, mock_city2]

        cities = host.list_cities()
        assert len(cities) == 2
        assert cities[0].city_code == "shanghai"
        assert cities[1].city_name  # default应该被翻译为"随机"

    @patch("backend.db_services.infras.host.SystemSettings.get_setting_value")
    @patch("backend.db_services.infras.host.LogicalCity.objects.all")
    def test_list_common_cities(self, mock_cities, mock_settings):
        """测试列出常用城市"""
        mock_city1 = MagicMock()
        mock_city1.name = "shanghai"
        mock_city2 = MagicMock()
        mock_city2.name = "beijing"

        mock_cities.return_value.order_by.return_value = [mock_city1, mock_city2]
        mock_settings.return_value = ["shanghai"]

        cities, common_cities = host.list_common_cities()
        assert len(common_cities) == 1
        assert common_cities[0].city_code == "shanghai"

    @patch("backend.db_services.infras.host.BKCity.objects.all")
    def test_list_logic_cities(self, mock_cities):
        """测试列出逻辑城市映射"""
        mock_city = MagicMock()
        mock_city.bk_idc_city_id = 1
        mock_city.bk_idc_city_name = "上海"
        mock_city.logical_city.name = "shanghai"

        mock_cities.return_value.order_by.return_value = [mock_city]

        logic_cities = host.list_logic_cities()
        assert len(logic_cities) == 1
        assert logic_cities[0]["logical_city_name"] == "shanghai"

    @patch("backend.db_services.infras.host.BKSubzone.objects.select_related")
    def test_list_subzones(self, mock_subzones):
        """测试列出子区域"""
        mock_zone = MagicMock()
        mock_zone.sub_zone_id = "zone1"
        mock_zone.bk_city.bk_idc_city_name = "shanghai"

        mock_subzones.return_value.all.return_value = [mock_zone]

        subzones = host.list_subzones()
        assert len(subzones) == 1
        assert subzones[0]["bk_city_code"] == "shanghai"

    @patch("backend.db_services.infras.host.BKSubzone.objects.select_related")
    def test_list_subzones_with_city_code(self, mock_subzones):
        """测试列出指定城市的子区域"""
        mock_subzones.return_value.all.return_value.filter.return_value = []

        host.list_subzones(city_code="shanghai")
        assert mock_subzones.return_value.all.return_value.filter.called

    def test_list_host_specs(self):
        """测试列出主机规格"""
        specs = host.list_host_specs()
        assert len(specs) > 0
        assert hasattr(specs[0], "cpu")
        assert hasattr(specs[0], "mem")

    def test_list_cap_specs_cache_resource_pool(self):
        """测试容量规格 - 资源池模式"""
        result = host.list_cap_specs_cache(ip_source=IpSource.RESOURCE_POOL)
        assert result == []

    def test_list_cap_specs_cache_small_cpu(self):
        """测试容量规格 - 小CPU"""
        result = host.list_cap_specs_cache(ip_source=IpSource.MANUAL_INPUT, cpu=2, mem=4096, ssd_disk=100, group=1)
        assert len(result) == 1
        assert result[0].shard_num == 4

    def test_list_cap_specs_cache_large_cpu(self):
        """测试容量规格 - 大CPU"""
        result = host.list_cap_specs_cache(ip_source=IpSource.MANUAL_INPUT, cpu=8, mem=16384, ssd_disk=500, group=2)
        assert len(result) > 0
        assert all(hasattr(spec, "cap_key") for spec in result)

    def test_list_cap_specs_tendisplus(self):
        """测试TendisPlus容量规格"""
        result = host.list_cap_specs_tendisplus(ip_source=IpSource.MANUAL_INPUT, cpu=4, mem=8, ssd_disk=200, group=3)
        assert len(result) == 1
        assert result[0].shard_num == 3
        assert result[0].maxmemory == 8

    def test_list_cap_specs_ssd(self):
        """测试SSD容量规格"""
        result = host.list_cap_specs_ssd(ip_source=IpSource.MANUAL_INPUT, cpu=16, mem=65536, ssd_disk=1000, group=2)
        assert len(result) > 0

    @patch("backend.db_services.infras.host.list_cities")
    def test_get_city_code_name_map(self, mock_list):
        """测试获取城市代码名称映射"""
        mock_list.return_value = [
            host.LCityModel("sh", "上海", "100", "sufficient"),
            host.LCityModel("bj", "北京", "200", "sufficient"),
        ]

        city_map = host.get_city_code_name_map()
        assert city_map["sh"] == "上海"
        assert city_map["bj"] == "北京"

    def test_get_spec_display_map(self):
        """测试获取规格显示映射"""
        spec_map = host.get_spec_display_map()
        assert len(spec_map) > 0
        assert all("-" in v for v in spec_map.values())
