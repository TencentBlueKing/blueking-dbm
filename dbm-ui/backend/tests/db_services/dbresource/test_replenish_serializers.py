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

from backend import env
from backend.components.hcm.client import HCMApi, HCMConfigError
from backend.components.hcm.constants import SUBZONE_ALL
from backend.db_services.dbresource.serializers import ResourceHcmReplenishSerializer

pytestmark = pytest.mark.django_db

REPLENISH_DATA = {
    "db_type": "mysql",
    "spec_id": 1,
    "city": "上海",
    "os_name": "tlinux 2.2",
    "count": 1,
}


class TestResourceHcmReplenishSerializer:
    @pytest.fixture(autouse=True)
    def mock_hcm_domain(self):
        with patch.object(env, "HCM_APIGW_DOMAIN", "https://hcm.example.com"):
            yield

    def test_subzone_all_with_unique_region(self):
        """subzone="*"（可用区全部 + 分 Campus（Camplus）生产）且城市可唯一定位云地域/可用区，校验通过"""
        data = {**REPLENISH_DATA, "subzone": SUBZONE_ALL}
        with patch.object(
            HCMApi, "get_region_zones_by_city", return_value=("ap-shanghai", ["ap-shanghai-1", "ap-shanghai-2"])
        ) as mocked_region:
            slz = ResourceHcmReplenishSerializer(data=data)
            assert slz.is_valid(), slz.errors

        mocked_region.assert_called_once_with("上海")

    def test_subzone_all_with_ambiguous_region(self):
        """subzone="*" 且城市无法唯一定位云地域，提交时即报校验错误，而非流程深处失败"""
        data = {**REPLENISH_DATA, "subzone": SUBZONE_ALL}
        with patch.object(HCMApi, "get_region_zones_by_city", side_effect=HCMConfigError("城市上海存在多个云地域")):
            slz = ResourceHcmReplenishSerializer(data=data)
            assert not slz.is_valid()
            assert "云地域" in str(slz.errors)

    def test_normal_subzone_skips_region_check(self):
        """普通园区不触发城市云地域校验"""
        data = {**REPLENISH_DATA, "subzone": "上海-一区"}
        with patch.object(HCMApi, "get_region_zones_by_city") as mocked_region:
            slz = ResourceHcmReplenishSerializer(data=data)
            assert slz.is_valid(), slz.errors

        mocked_region.assert_not_called()
