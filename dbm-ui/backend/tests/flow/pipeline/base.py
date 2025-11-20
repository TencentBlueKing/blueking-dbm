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
import uuid
from typing import Any, Dict, List, Type

from django.test import TestCase

from backend.tests.utils.pipeline_test_utils import PipelineTestUtils


class BasePipelineTest(TestCase):
    """
    流程测试基类
    提供通用的测试方法和工具
    """

    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        pass

    def setUp(self):
        """每个测试方法执行前的设置"""
        # 生成唯一的测试ID
        self.root_id = uuid.uuid4().hex[:24]

    def execute_pipeline_test(
        self,
        flow_class: Type,
        flow_method: str,
        mock_data: Dict[str, Any] = None,
        additional_params: Dict[str, Any] = None,
        additional_mocks: List[Dict[str, Any]] = None,
        expect_failure: bool = False,
        expected_error_message: str = None,
    ) -> Any:
        """
        执行流程测试

        Args:
            flow_class: 流程类
            flow_method: 要测试的流程方法名称
            mock_data: 自定义参数，会覆盖默认参数
            additional_params: 额外需要的参数
            additional_mocks: 额外需要模拟的模块和方法
            expect_failure: 是否期望Pipeline验证失败
            expected_error_message: 期望的错误消息，如果expect_failure为True，则可以指定期望的错误消息

        Returns:
            Any: 流程方法的返回值
        """
        return PipelineTestUtils.execute_pipeline_test(
            flow_class=flow_class,
            flow_method=flow_method,
            root_id=self.root_id,
            mock_data=mock_data,
            additional_params=additional_params,
            additional_mocks=additional_mocks,
            expect_failure=expect_failure,
            expected_error_message=expected_error_message,
            assertion_style="unittest",
            test_case_instance=self,
        )
