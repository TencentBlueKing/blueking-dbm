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

from backend.components.hcm.client import HCMApi, HCMConfigError
from backend.components.hcm.constants import ANTI_AFFINITY_LEVEL_ANTI_CAMPUS, RES_ASSIGN_SPLIT_CAMPUS, SUBZONE_ALL
from backend.db_meta.models.city_map import BKCity, BKSubzone

pytestmark = pytest.mark.django_db


@pytest.fixture
def subzone_fixture():
    """构造园区数据：
    - 上海：两个园区归属同一云地域且可用区各不相同，另有一条未配置云地域的脏数据（应被忽略）
    - 南京：两个园区归属不同云地域（无法唯一推导）
    - 仪征：园区云地域有效但未配置云可用区（zones 为空，不允许提单）
    """
    shanghai = BKCity.objects.get(bk_idc_city_name="上海")
    nanjing = BKCity.objects.get(bk_idc_city_name="南京")
    yizheng = BKCity.objects.get(bk_idc_city_name="仪征")
    subzones = [
        BKSubzone(bk_sub_zone="上海-一区", bk_city=shanghai, bk_cloud_region="ap-shanghai", bk_cloud_zone="ap-shanghai-1"),
        BKSubzone(bk_sub_zone="上海-二区", bk_city=shanghai, bk_cloud_region="ap-shanghai", bk_cloud_zone="ap-shanghai-2"),
        BKSubzone(bk_sub_zone="上海-三区", bk_city=shanghai, bk_cloud_region="", bk_cloud_zone="ap-shanghai-3"),
        BKSubzone(bk_sub_zone="南京-一区", bk_city=nanjing, bk_cloud_region="ap-nanjing", bk_cloud_zone="ap-nanjing-1"),
        BKSubzone(bk_sub_zone="南京-二区", bk_city=nanjing, bk_cloud_region="ap-nanjing-2", bk_cloud_zone="ap-nanjing-2"),
        BKSubzone(bk_sub_zone="仪征-一区", bk_city=yizheng, bk_cloud_region="ap-yizheng", bk_cloud_zone=""),
    ]
    for subzone in subzones:
        subzone.save()

    yield subzones

    BKSubzone.objects.filter(bk_sub_zone__in=[s.bk_sub_zone for s in subzones]).delete()


class TestGetRegionZonesByCity:
    def test_unique_region_with_zones(self, subzone_fixture):
        # 上海下有效园区归属同一云地域，可唯一推导；可用区为实际值去重列表，空地域脏记录被忽略
        assert HCMApi.get_region_zones_by_city("上海") == ("ap-shanghai", ["ap-shanghai-1", "ap-shanghai-2"])

    def test_city_not_found(self, subzone_fixture):
        with pytest.raises(HCMConfigError):
            HCMApi.get_region_zones_by_city("不存在的城市")

    def test_only_empty_region(self, subzone_fixture):
        # 城市下园区全部未配置云地域，视为无法推导，而不是返回空地域
        BKSubzone.objects.filter(bk_sub_zone="仪征-一区").update(bk_cloud_region="")
        with pytest.raises(HCMConfigError):
            HCMApi.get_region_zones_by_city("仪征")

    def test_empty_zone(self, subzone_fixture):
        # 云地域有效但可用区全部为空，海磊要求传实际可用区，无法提单
        with pytest.raises(HCMConfigError, match="云可用区"):
            HCMApi.get_region_zones_by_city("仪征")

    def test_multiple_regions(self, subzone_fixture):
        with pytest.raises(HCMConfigError):
            HCMApi.get_region_zones_by_city("南京")


class TestResolveRegionZone:
    def test_with_subzone_all(self, subzone_fixture):
        region, zone, zones = HCMApi._resolve_region_zone(SUBZONE_ALL, "上海")
        assert region == "ap-shanghai"
        assert zone is None
        assert zones == ["ap-shanghai-1", "ap-shanghai-2"]

    def test_with_normal_subzone(self, subzone_fixture):
        region, zone, zones = HCMApi._resolve_region_zone("上海-一区", "上海")
        assert (region, zone) == ("ap-shanghai", "ap-shanghai-1")
        assert zones is None

    def test_subzone_all_without_city(self, subzone_fixture):
        with pytest.raises(HCMConfigError):
            HCMApi._resolve_region_zone(SUBZONE_ALL, "")

    def test_subzone_not_found(self, subzone_fixture):
        with pytest.raises(HCMConfigError):
            HCMApi._resolve_region_zone("不存在的园区", "上海")


class TestFillZoneInfo:
    def test_with_zone(self):
        spec = {}
        HCMApi._fill_zone_info(spec, "ap-shanghai-1", None)
        assert spec == {"zone": "ap-shanghai-1"}

    def test_without_zone(self):
        # 海磊不允许 zones 传 "all"，必须传实际可用区列表；同时传 res_assign + anti_affinity_level
        spec = {}
        HCMApi._fill_zone_info(spec, None, ["ap-shanghai-1", "ap-shanghai-2"])
        assert spec == {
            "zones": ["ap-shanghai-1", "ap-shanghai-2"],
            "res_assign": RES_ASSIGN_SPLIT_CAMPUS,
            "anti_affinity_level": ANTI_AFFINITY_LEVEL_ANTI_CAMPUS,
        }


class TestCreateApply:
    APPLY_KWARGS = dict(
        bk_biz_id="2005000002",
        username="admin",
        city="上海",
        os_name="tlinux 2.2",
        device_types=["S5.MEDIUM8", "S5.LARGE8"],
        disk=[],
        count=2,
        ticket_id=1,
    )

    @patch("backend.components.hcm.client.get_hcm_apply_resource_biz", return_value=2005000002)
    @patch("backend.components.hcm.client.CCApi.list_biz_hosts")
    @patch("backend.components.hcm.client.SystemSettings.get_setting_value", return_value={"tlinux 2.2": "img-1"})
    @patch.object(HCMApi, "create_biz_apply", return_value={"order_id": "order-1"})
    def test_spec_with_subzone_all(self, mocked_apply, mocked_setting, mocked_cc, mocked_biz, subzone_fixture):
        mocked_cc.return_value = {"info": [{"bk_cloud_inst_id": "ins-1"}]}
        order_id = HCMApi.create_apply(subzone=SUBZONE_ALL, **self.APPLY_KWARGS)

        assert order_id == "order-1"
        spec = mocked_apply.call_args.kwargs["params"]["suborders"][0]["spec"]
        assert spec["region"] == "ap-shanghai"
        # zones 必须是实际可用区列表，不允许传 "all"
        assert spec["zones"] == ["ap-shanghai-1", "ap-shanghai-2"]
        assert spec["res_assign"] == RES_ASSIGN_SPLIT_CAMPUS
        assert spec["anti_affinity_level"] == ANTI_AFFINITY_LEVEL_ANTI_CAMPUS
        assert "zone" not in spec

    @patch("backend.components.hcm.client.get_hcm_apply_resource_biz", return_value=2005000002)
    @patch("backend.components.hcm.client.CCApi.list_biz_hosts")
    @patch("backend.components.hcm.client.SystemSettings.get_setting_value", return_value={"tlinux 2.2": "img-1"})
    @patch.object(HCMApi, "create_biz_apply", return_value={"order_id": "order-1"})
    def test_spec_with_normal_subzone(self, mocked_apply, mocked_setting, mocked_cc, mocked_biz, subzone_fixture):
        mocked_cc.return_value = {"info": [{"bk_cloud_inst_id": "ins-1"}]}
        HCMApi.create_apply(subzone="上海-一区", **self.APPLY_KWARGS)

        spec = mocked_apply.call_args.kwargs["params"]["suborders"][0]["spec"]
        assert spec["region"] == "ap-shanghai"
        assert spec["zone"] == "ap-shanghai-1"
        assert "zones" not in spec
        assert "res_assign" not in spec
        assert "anti_affinity_level" not in spec

    @patch("backend.components.hcm.client.get_hcm_apply_resource_biz", return_value=2005000002)
    @patch("backend.components.hcm.client.CCApi.list_biz_hosts")
    @patch("backend.components.hcm.client.SystemSettings.get_setting_value", return_value={"tlinux 2.2": "img-1"})
    @patch.object(HCMApi, "create_biz_apply")
    def test_config_error_fail_fast(self, mocked_apply, mocked_setting, mocked_cc, mocked_biz, subzone_fixture):
        # 城市无法唯一定位云地域时，直接抛配置类错误，不应发起任何远程调用
        with pytest.raises(HCMConfigError):
            HCMApi.create_apply(subzone=SUBZONE_ALL, **{**self.APPLY_KWARGS, "city": "南京"})

        mocked_cc.assert_not_called()
        mocked_apply.assert_not_called()

    @patch("backend.components.hcm.client.get_hcm_apply_resource_biz", return_value=2005000002)
    @patch("backend.components.hcm.client.CCApi.list_biz_hosts")
    @patch("backend.components.hcm.client.SystemSettings.get_setting_value", return_value={"tlinux 2.2": "img-1"})
    @patch.object(HCMApi, "create_biz_apply")
    def test_empty_zone_fail_fast(self, mocked_apply, mocked_setting, mocked_cc, mocked_biz, subzone_fixture):
        # 城市无实际可用区（海磊要求传实际 zone），直接抛配置类错误
        with pytest.raises(HCMConfigError, match="云可用区"):
            HCMApi.create_apply(subzone=SUBZONE_ALL, **{**self.APPLY_KWARGS, "city": "仪征"})

        mocked_cc.assert_not_called()
        mocked_apply.assert_not_called()

    @patch("backend.components.hcm.client.get_hcm_apply_resource_biz", return_value=2005000002)
    @patch("backend.components.hcm.client.CCApi.list_biz_hosts")
    @patch("backend.components.hcm.client.SystemSettings.get_setting_value", return_value={})
    @patch.object(HCMApi, "create_biz_apply")
    def test_image_not_found_fail_fast(self, mocked_apply, mocked_setting, mocked_cc, mocked_biz, subzone_fixture):
        # 镜像缺失属于配置类错误，直接抛出
        with pytest.raises(HCMConfigError):
            HCMApi.create_apply(subzone=SUBZONE_ALL, **self.APPLY_KWARGS)

        mocked_cc.assert_not_called()
        mocked_apply.assert_not_called()


class TestModifyApply:
    MODIFY_KWARGS = dict(
        suborder_id="suborder-1",
        bk_biz_id="2005000002",
        ticket_id=1,
        username="admin",
        city="上海",
        os_name="tlinux 2.2",
        device_types=["S5.MEDIUM8"],
        disk=[],
        count=1,
    )

    @patch("backend.components.hcm.client.get_hcm_apply_resource_biz", return_value=2005000002)
    @patch("backend.components.hcm.client.SystemSettings.get_setting_value", return_value={"tlinux 2.2": "img-1"})
    @patch.object(HCMApi, "modify_biz_apply")
    def test_spec_with_subzone_all(self, mocked_modify, mocked_setting, mocked_biz, subzone_fixture):
        HCMApi.modify_apply(subzone=SUBZONE_ALL, **self.MODIFY_KWARGS)

        spec = mocked_modify.call_args.kwargs["params"]["spec"]
        assert spec["region"] == "ap-shanghai"
        assert spec["zones"] == ["ap-shanghai-1", "ap-shanghai-2"]
        assert spec["res_assign"] == RES_ASSIGN_SPLIT_CAMPUS
        assert spec["anti_affinity_level"] == ANTI_AFFINITY_LEVEL_ANTI_CAMPUS
        assert "zone" not in spec

    @patch("backend.components.hcm.client.get_hcm_apply_resource_biz", return_value=2005000002)
    @patch("backend.components.hcm.client.SystemSettings.get_setting_value", return_value={"tlinux 2.2": "img-1"})
    @patch.object(HCMApi, "modify_biz_apply")
    def test_spec_with_normal_subzone(self, mocked_modify, mocked_setting, mocked_biz, subzone_fixture):
        HCMApi.modify_apply(subzone="上海-一区", **self.MODIFY_KWARGS)

        spec = mocked_modify.call_args.kwargs["params"]["spec"]
        assert spec["zone"] == "ap-shanghai-1"
        assert "zones" not in spec
        assert "res_assign" not in spec
        assert "anti_affinity_level" not in spec
