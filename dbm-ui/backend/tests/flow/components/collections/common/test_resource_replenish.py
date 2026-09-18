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

from backend.components.hcm.client import HCMApi
from backend.components.hcm.constants import SUBZONE_ALL
from backend.flow.plugins.components.collections.common.resource_replenish import HCMResourceReplenishService

# __find_candidate_device 为名称改写的私有方法，这里取出未绑定函数直接调用
_find_candidate_device = HCMResourceReplenishService._HCMResourceReplenishService__find_candidate_device


class _FakeService:
    """__find_candidate_device 仅依赖 self.CANDIDATE_DEVICE_NUM，用轻量对象替代真实服务实例"""

    CANDIDATE_DEVICE_NUM = HCMResourceReplenishService.CANDIDATE_DEVICE_NUM


@pytest.fixture
def spec():
    return SimpleNamespace(device_class=["S5.MEDIUM8", "S5.LARGE8", "S5.2XLARGE32"])


class TestFindCandidateDevice:
    def test_subzone_all_skips_capacity_check(self, spec):
        # subzone="*" 跳过单园区容量预检，直接返回当前候选机型下标
        kwargs = {"subzone": SUBZONE_ALL}
        assert _find_candidate_device(_FakeService(), spec, kwargs, 1) == 1

    def test_subzone_all_exhausted(self, spec):
        kwargs = {"subzone": SUBZONE_ALL}
        with pytest.raises(Exception, match="库存容量"):
            _find_candidate_device(_FakeService(), spec, kwargs, 3)

    def test_normal_subzone_picks_first_with_capacity(self, spec):
        kwargs = {"subzone": "上海-一区"}
        with patch.object(HCMApi, "get_cvm_device_capacity", side_effect=[0, 5]):
            assert _find_candidate_device(_FakeService(), spec, kwargs, 0) == 1

    def test_normal_subzone_exhausted(self, spec):
        kwargs = {"subzone": "上海-一区"}
        with patch.object(HCMApi, "get_cvm_device_capacity", return_value=0):
            with pytest.raises(Exception, match="库存容量"):
                _find_candidate_device(_FakeService(), spec, kwargs, 0)
