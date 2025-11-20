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
from unittest.mock import MagicMock, patch

from backend.tests.mock_data.components.engine_run_pipeline import EngineApiMock


class PipelineTestUtils:
    """
    Pipeline测试工具类，提供通用的测试方法
    """

    @staticmethod
    def execute_pipeline_test(
        flow_class: Type,
        flow_method: str,
        root_id: str = None,
        mock_data: Dict[str, Any] = None,
        additional_params: Dict[str, Any] = None,
        additional_mocks: List[Dict[str, Any]] = None,
        expect_failure: bool = False,
        expected_error_message: str = None,
        assertion_style: str = "pytest",  # "pytest" or "unittest"
        test_case_instance=None,  # unittest.TestCase instance for unittest style
    ) -> Any:
        """
        执行流程测试

        Args:
            flow_class: 流程类
            flow_method: 要测试的流程方法名称
            root_id: 流程根ID，如果为None则自动生成
            mock_data: 自定义参数，会覆盖默认参数
            additional_params: 额外需要的参数
            additional_mocks: 额外需要模拟的模块和方法
            expect_failure: 是否期望Pipeline验证失败
            expected_error_message: 期望的错误消息，如果expect_failure为True，则可以指定期望的错误消息
            assertion_style: 断言风格，"pytest" 或 "unittest"
            test_case_instance: unittest.TestCase实例，用于unittest风格的断言

        Returns:
            Any: 流程方法的返回值
        """
        # 如果没有提供root_id，则生成一个
        if root_id is None:
            root_id = uuid.uuid4().hex[:24]

        # 创建流程实例
        flow_instance = flow_class(root_id=root_id, data=mock_data)
        # 重置EngineApiMock的状态
        EngineApiMock.was_called = False
        EngineApiMock.last_result = None
        EngineApiMock.last_exception = None

        # 准备所有需要模拟的对象
        patchers = []

        # 添加默认的pipeline mock
        pipeline_patch = patch("bamboo_engine.api.run_pipeline", side_effect=EngineApiMock.run_pipeline)
        patchers.append(pipeline_patch)

        # 添加额外的模拟对象
        if additional_mocks:
            for mock_config in additional_mocks:
                target = mock_config.get("target")
                side_effect = mock_config.get("side_effect")
                return_value = mock_config.get("return_value")

                if side_effect:
                    patchers.append(patch(target, side_effect=side_effect))
                elif return_value is not None:
                    patchers.append(patch(target, return_value=return_value))
                else:
                    # 如果没有指定side_effect或return_value，则使用MagicMock
                    patchers.append(patch(target, new=MagicMock()))

        # 启动所有patchers
        [patcher.start() for patcher in patchers]

        try:
            # 获取要测试的方法
            flow_method_to_test = getattr(flow_instance, flow_method)

            # 执行流程方法（可能返回None，即使成功）
            result = flow_method_to_test()

            # 检查EngineApiMock是否被调用
            PipelineTestUtils._assert_engine_called(assertion_style, test_case_instance)

            # 验证执行结果
            if expect_failure:
                PipelineTestUtils._assert_pipeline_failed(assertion_style, expected_error_message, test_case_instance)
            else:
                PipelineTestUtils._assert_pipeline_succeeded(assertion_style, test_case_instance)

            return result

        except Exception as e:
            if expect_failure:
                if expected_error_message:
                    PipelineTestUtils._assert_error_message_in_exception(
                        assertion_style, expected_error_message, str(e), test_case_instance
                    )
                return None
            else:
                raise
        finally:
            # 停止所有patchers
            for patcher in patchers:
                patcher.stop()

    @staticmethod
    def _assert_engine_called(assertion_style: str, test_case_instance=None):
        """断言引擎被调用"""
        if assertion_style == "pytest":
            assert EngineApiMock.was_called, "Pipeline engine should be called"
        else:  # unittest
            if test_case_instance is None:
                raise ValueError("test_case_instance is required for unittest assertion style")
            test_case_instance.assertTrue(EngineApiMock.was_called, "Pipeline engine should be called")

    @staticmethod
    def _assert_pipeline_failed(assertion_style: str, expected_error_message: str = None, test_case_instance=None):
        """断言pipeline执行失败"""
        if assertion_style == "pytest":
            assert not EngineApiMock.last_result.result, "Pipeline validation should fail"
            if expected_error_message:
                assert expected_error_message in EngineApiMock.last_result.message, (
                    f"Expected error message '{expected_error_message}' not found in actual message: "
                    f"'{EngineApiMock.last_result.message}'"
                )
        else:  # unittest
            if test_case_instance is None:
                raise ValueError("test_case_instance is required for unittest assertion style")
            test_case_instance.assertFalse(EngineApiMock.last_result.result, "Pipeline validation should fail")
            if expected_error_message:
                test_case_instance.assertIn(
                    expected_error_message,
                    EngineApiMock.last_result.message,
                    f"Expected error message '{expected_error_message}' not found in actual message: "
                    f"'{EngineApiMock.last_result.message}'",
                )

    @staticmethod
    def _assert_pipeline_succeeded(assertion_style: str, test_case_instance=None):
        """断言pipeline执行成功"""
        if assertion_style == "pytest":
            assert (
                EngineApiMock.last_result.result
            ), f"Pipeline validation should pass, but failed with message: {EngineApiMock.last_result.message}"
        else:  # unittest
            if test_case_instance is None:
                raise ValueError("test_case_instance is required for unittest assertion style")
            test_case_instance.assertTrue(
                EngineApiMock.last_result.result,
                f"Pipeline validation should pass, but failed with message: " f"{EngineApiMock.last_result.message}",
            )

    @staticmethod
    def _assert_error_message_in_exception(
        assertion_style: str, expected_error_message: str, exception_str: str, test_case_instance=None
    ):
        """断言异常消息中包含期望的错误消息"""
        if assertion_style == "pytest":
            assert (
                expected_error_message in exception_str
            ), f"Expected error message '{expected_error_message}' not found in actual exception: '{exception_str}'"
        else:  # unittest
            if test_case_instance is None:
                raise ValueError("test_case_instance is required for unittest assertion style")
            test_case_instance.assertIn(
                expected_error_message,
                exception_str,
                f"Expected error message '{expected_error_message}' not found in actual exception: '{exception_str}'",
            )
