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

import logging
from abc import ABC
from typing import Any, List, NoReturn, Type, Union

import pytest
from mock import MagicMock, patch
from pipeline.component_framework.component import Component
from pipeline.component_framework.test import ComponentTestCase, ComponentTestMixin, Patcher

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


class BaseComponentTest(ComponentTestMixin, ABC):
    """
    组件单元测试的基类，子类可覆写对应的函数来实现对组件的自定义测试
    """

    @classmethod
    def setUpTestData(cls) -> Union[Any, NoReturn]:
        """每个测试类启动前的数据准备"""
        super(BaseComponentTest, cls).setUpTestData()

    @classmethod
    def setUpClass(cls) -> Union[Any, NoReturn]:
        """每个测试类启动的前置函数"""
        super(BaseComponentTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls) -> Union[Any, NoReturn]:
        """每个测试类启动的后置函数"""
        super(BaseComponentTest, cls).tearDownClass()

    def setUp(self) -> Union[Any, NoReturn]:
        """每个测试样例启动的前置函数"""
        pass

    def tearDown(self) -> Union[Any, NoReturn]:
        """每个测试样例启动的后置函数"""
        pass

    def component_cls(self) -> Type[Component]:
        """待测试的component的类"""
        raise NotImplementedError()

    def cases(self) -> List[ComponentTestCase]:
        """组件测试样例"""
        raise NotImplementedError()


class BaseComponentPatcher(Patcher):
    def __init__(self, target, new=None, return_value=None, side_effect=None) -> None:
        super().__init__(target, return_value, side_effect)
        self.new = new

    def mock_patcher(self):
        if self.new:
            return patch(target=self.target, new=self.new)

        return patch(target=self.target, new=MagicMock(return_value=self.return_value, side_effect=self.side_effect))
