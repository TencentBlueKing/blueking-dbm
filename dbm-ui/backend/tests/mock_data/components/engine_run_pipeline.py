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
from unittest.mock import MagicMock

from bamboo_engine import validator as real_validator

logger = logging.getLogger("test")


# 创建mock版本的类和模块
class MockEngine:
    def __init__(self, runtime=None):
        self.runtime = runtime or MagicMock()


# 创建EngineAPIResult的模拟类，避免直接导入bamboo_engine
class MockEngineAPIResult:
    def __init__(self, result=True, message="", exc=None, data=None, exc_trace=None, root_id=None):
        self.result = result
        self.message = message
        self.exc = exc
        self.data = data
        self.exc_trace = exc_trace
        self.root_id = root_id


class EngineApiMock:
    # 记录api.run_pipeline被调用的状态
    was_called = False
    last_result = None
    last_exception = None

    @classmethod
    def run_pipeline(cls, pipeline=None, **kwargs):
        """
        模拟api.run_pipeline方法，直接调用Engine.run_pipeline
        但Engine.run_pipeline被模拟为只执行到validator.validate_and_process_pipeline步骤
        """
        cls.was_called = True
        logger.info(f"Mock api.run_pipeline called for pipeline {pipeline.get('id', 'unknown')}")

        try:
            # 只执行验证步骤
            cycle_tolerate = kwargs.get("cycle_tolerate", False)
            # 使用真实的validator进行验证
            real_validator.validate_and_process_pipeline(pipeline, cycle_tolerate)
            logger.info("Real validator.validate_and_process_pipeline passed")

            # 创建并存储一个成功结果
            cls.last_result = MockEngineAPIResult(
                result=True,
                message="Pipeline validation successful",
                exc=None,
                data={"validated": True},
                exc_trace=None,
                root_id=pipeline.get("id", None),
            )
            return cls.last_result
        except Exception as e:
            # 如果验证失败，存储并返回错误结果
            logger.error(f"Pipeline validation failed: {str(e)}")
            cls.last_exception = e
            cls.last_result = MockEngineAPIResult(
                result=False,
                message=f"Pipeline validation failed: {str(e)}",
                exc=e,
                data={"validated": False},
                exc_trace=str(e),
            )
            return cls.last_result
