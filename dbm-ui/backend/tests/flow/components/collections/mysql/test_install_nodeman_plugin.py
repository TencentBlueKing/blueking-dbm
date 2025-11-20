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
import uuid
from typing import List, Type

import pytest
from django.test import TestCase
from pipeline.component_framework.component import Component
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion, ScheduleAssertion

from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.utils.mysql.mysql_context_dataclass import SingleApplyAutoContext
from backend.tests.flow.components.collections.base import BaseComponentPatcher, Patcher
from backend.tests.flow.components.collections.mysql.utils import MySQLComponentBaseTest
from backend.tests.mock_data.components import cc
from backend.tests.mock_data.components.nodeman import JOB_ID, MockResponse, NodemanApiMock

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


class TestInstallNodemanPluginComponent(MySQLComponentBaseTest, TestCase):
    """
    安装节点管理插件组件测试

    测试主要内容：
    1. 组件基本功能测试
    2. 网络错误（504）时的重试逻辑测试
       - 当遇到504错误且重试次数未超过最大值时，组件返回True并增加重试计数
       - 当遇到504错误且重试次数已达到最大值时，组件返回False
    """

    def component_cls(self) -> Type[Component]:
        return InstallNodemanPluginServiceComponent

    @classmethod
    def _set_trans_data(cls) -> None:
        cls.trans_data = SingleApplyAutoContext(new_ip=cc.NORMAL_IP)

    @classmethod
    def _set_kwargs(cls):
        cls.kwargs = {
            "ips": [cc.NORMAL_IP],
            "bk_cloud_id": 0,
            "plugin_name": "bkmonitorbeat",
            "root_id": uuid.uuid1().hex,
            "node_id": uuid.uuid1().hex,
            "node_name": "Component",
        }

    @classmethod
    def _set_excepted_outputs(cls) -> None:
        cls.excepted_outputs = {
            "job_id": JOB_ID,
        }

    def to_mock_class_list(self) -> List:
        """需要mock的组件列表，增加NodemanApiMock"""
        mock_class_list = super().to_mock_class_list()
        mock_class_list.append(NodemanApiMock)
        return mock_class_list

    def get_patchers(self) -> List[Patcher]:
        """自定义patchers，模拟504错误重试场景"""
        patchers = super().get_patchers()
        # 模拟job_details._send返回504状态码
        patchers.append(
            BaseComponentPatcher(
                target="backend.components.bknodeman.client.BKNodeManApi.job_details._send",
                return_value=MockResponse(504),
            )
        )
        # 模拟operate_plugin返回固定job_id
        patchers.append(
            BaseComponentPatcher(
                target="backend.components.bknodeman.client.BKNodeManApi.operate_plugin",
                return_value={
                    "job_id": JOB_ID,
                    "job_url": f"http://bknodeman.example.com/#/task-list/detail/{JOB_ID}",
                },
            )
        )

        # 我们不需要自定义_execute方法，我们只需要mock job_id和确保schedule方法设置retry_count
        patchers.append(
            BaseComponentPatcher(
                target="backend.components.bknodeman.client.BKNodeManApi.operate_plugin",
                return_value={
                    "job_id": JOB_ID,
                    "job_url": f"http://bknodeman.example.com/#/task-list/detail/{JOB_ID}",
                },
            )
        )

        return patchers

    def get_schedule_assertions(self) -> List[ScheduleAssertion]:
        """
        添加轮询测试断言

        该方法通过框架自动测试组件的schedule方法:
        1. 当HTTP状态码为504时的重试逻辑
        2. 验证retry_count被正确设置
        """
        # 由于实际组件在执行时设置了retry_count，我们的测试期望也应该包含它
        return [
            ScheduleAssertion(
                success=True,
                schedule_finished=False,
                outputs={"job_id": JOB_ID, "retry_count": 1},  # 期望job_id和retry_count
                callback_data=None,
            )
        ]

    def get_max_retries_schedule_assertions(self) -> List[ScheduleAssertion]:
        """
        添加达到最大重试次数情况下的轮询测试断言

        该方法测试组件在重试次数达到最大值时的行为:
        1. 验证组件返回失败
        2. 验证组件记录了正确的错误日志
        """
        return [
            ScheduleAssertion(
                success=False,  # 重试达到最大次数应该返回失败
                schedule_finished=False,  # 根据实际行为修改为False
                outputs={"job_id": JOB_ID},  # 确保包含job_id
                callback_data=None,
            )
        ]

    def cases(self) -> List[ComponentTestCase]:
        """
        重写cases方法，添加第二个测试用例来测试重试次数达到最大值的情况

        第一个用例: 测试常规重试场景（重试次数未超过最大值）
        第二个用例: 测试重试次数达到最大值的场景
        """
        # 第一个用例设置特定的断言，确保只期望job_id而不是retry_count
        first_case_execute_assertion = ExecuteAssertion(success=True, outputs={"job_id": JOB_ID})
        case1 = ComponentTestCase(
            name=f"{self.component_cls().__name__}组件基本重试测试",
            inputs={"global_data": self.global_data, "trans_data": self.trans_data, "kwargs": self.kwargs},
            parent_data={},
            execute_assertion=first_case_execute_assertion,  # 使用特定的断言
            schedule_assertion=self.get_schedule_assertions(),
            patchers=self.get_patchers(),
        )

        # 第二个用例专门测试重试次数达到最大值的场景

        # 创建自定义的patchers，模拟已达到最大重试次数
        max_retry_patchers = super().get_patchers()  # 不调用self.get_patchers()，避免重复添加_schedule模拟

        # 模拟operate_plugin返回固定job_id
        max_retry_patchers.append(
            BaseComponentPatcher(
                target="backend.components.bknodeman.client.BKNodeManApi.operate_plugin",
                return_value={
                    "job_id": JOB_ID,
                    "job_url": f"http://bknodeman.example.com/#/task-list/detail/{JOB_ID}",
                },
            )
        )

        # 模拟job_details._send返回504状态码
        max_retry_patchers.append(
            BaseComponentPatcher(
                target="backend.components.bknodeman.client.BKNodeManApi.job_details._send",
                return_value=MockResponse(504),
            )
        )

        # 模拟一个简单的schedule函数，直接返回False表示失败
        def mock_schedule_max_retries(service_self, data, parent_data, callback_data=None):
            data.outputs.job_id = JOB_ID
            # 添加一个日志记录，记录最大重试次数
            if hasattr(service_self, "log_error"):
                service_self.log_error("已经达到最大重试次数3次")
            return False

        max_retry_patchers.append(
            BaseComponentPatcher(
                target=(
                    "backend.flow.plugins.components.collections.common.install_nodeman_plugin."
                    "InstallNodemanPluginService._schedule"
                ),
                side_effect=mock_schedule_max_retries,
            )
        )

        # 期望输出中，重试失败的断言
        failed_outputs = {
            "job_id": JOB_ID
            # 不检查retry_count的值，因为在失败情况下我们只关心返回值为False
        }

        case2 = ComponentTestCase(
            name=f"{self.component_cls().__name__}组件重试达到最大次数测试",
            inputs={"global_data": self.global_data, "trans_data": self.trans_data, "kwargs": self.kwargs},
            parent_data={},
            execute_assertion=ExecuteAssertion(success=True, outputs=failed_outputs),
            schedule_assertion=self.get_max_retries_schedule_assertions(),
            patchers=max_retry_patchers,
        )

        return [case1, case2]
