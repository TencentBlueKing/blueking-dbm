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

from backend.components.exception import DataAPIException
from backend.components.hcm.client import HCMApi
from backend.components.hcm.constants import ANTI_AFFINITY_LEVEL_ANTI_CAMPUS, RES_ASSIGN_SPLIT_CAMPUS, SUBZONE_ALL
from backend.db_meta.models.city_map import BKCity, BKSubzone

pytestmark = pytest.mark.django_db


@pytest.fixture
def subzone_fixture():
    """构造园区数据：上海两个园区，分别对应不同的云可用区"""
    shanghai = BKCity.objects.get(bk_idc_city_name="上海")
    subzones = [
        BKSubzone(bk_sub_zone="上海-一区", bk_city=shanghai, bk_cloud_region="ap-shanghai", bk_cloud_zone="ap-shanghai-1"),
        BKSubzone(bk_sub_zone="上海-二区", bk_city=shanghai, bk_cloud_region="ap-shanghai", bk_cloud_zone="ap-shanghai-2"),
    ]
    for subzone in subzones:
        subzone.save()

    yield subzones

    BKSubzone.objects.filter(bk_sub_zone__in=[s.bk_sub_zone for s in subzones]).delete()


class TestGetRegionByCity:
    def test_city_with_region(self, subzone_fixture):
        # 同城园区归属同一云地域，取任意一个有效值即可
        assert HCMApi.get_region_by_city("上海") == "ap-shanghai"

    def test_city_without_region(self, subzone_fixture):
        with pytest.raises(DataAPIException):
            HCMApi.get_region_by_city("不存在的城市")


class TestResolveRegionZone:
    def test_with_subzone_all(self, subzone_fixture):
        # 可用区全部：zone 为空（提单改传 zones=["all"]），region 由城市关联查询
        assert HCMApi._resolve_region_zone(SUBZONE_ALL, "上海") == ("ap-shanghai", None)

    def test_with_subzone_all_without_city(self, subzone_fixture):
        with pytest.raises(DataAPIException):
            HCMApi._resolve_region_zone(SUBZONE_ALL, "")

    def test_with_normal_subzone(self, subzone_fixture):
        assert HCMApi._resolve_region_zone("上海-一区", "上海") == ("ap-shanghai", "ap-shanghai-1")

    def test_subzone_not_found(self, subzone_fixture):
        with pytest.raises(DataAPIException):
            HCMApi._resolve_region_zone("不存在的园区", "上海")


class TestFillZoneInfo:
    def test_with_zone(self):
        spec = {}
        HCMApi._fill_zone_info(spec, "ap-shanghai-1")
        assert spec == {"zone": "ap-shanghai-1"}

    def test_without_zone(self):
        # 可用区全部：zones 传 ["all"]，同时传 res_assign + anti_affinity_level 表达分 Campus 生产
        spec = {}
        HCMApi._fill_zone_info(spec, None)
        assert spec == {
            "zones": [SUBZONE_ALL],
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
        # 可用区全部：region 由城市关联查询得到，可用区改传 zones=["all"]
        assert spec["region"] == "ap-shanghai"
        assert spec["zones"] == [SUBZONE_ALL]
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
    @patch("backend.components.hcm.client.SystemSettings.get_setting_value", return_value={})
    @patch.object(HCMApi, "create_biz_apply")
    def test_image_not_found_fail_fast(self, mocked_apply, mocked_setting, mocked_cc, mocked_biz, subzone_fixture):
        # 镜像缺失属于配置类错误，直接抛出
        with pytest.raises(DataAPIException):
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
        assert spec["zones"] == [SUBZONE_ALL]
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
