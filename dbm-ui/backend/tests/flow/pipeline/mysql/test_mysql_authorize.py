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
import pytest

from backend.flow.engine.bamboo.scene.mysql.mysql_authorize_rules import MySQLAuthorizeRulesFlows
from backend.tests.flow.pipeline.base import BasePipelineTest
from backend.tests.mock_data.components.mysql_priv_manager import DBPrivManagerApiMock
from backend.tests.mock_data.flow.pipeline.collections.mysql import MYSQL_AUTHORIZE_RULES_PARAMS

pytestmark = pytest.mark.django_db


class TestMySQLAuthorize(BasePipelineTest):
    """
    测试MySQLAuthorizeRulesFlows类的方法
    使用BasePipelineTest可以简化测试代码
    """

    def test_mysql_authorize_mock(self):
        """
        测试MySQLAuthorizeRulesFlows类的authorize_mysql_rules_v2方法
        验证pipeline是否正确构建并通过验证步骤，但不执行实际的pipeline
        """
        # 添加所需要的mock
        additional_mocks = [
            {
                "target": "backend.components.mysql_priv_manager.client._DBPrivManagerApi",
                "return_value": DBPrivManagerApiMock(),
            },
            {
                "target": "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi",
                "return_value": DBPrivManagerApiMock(),
            },
        ]

        # 使用测试框架执行测试
        self.execute_pipeline_test(
            mock_data=MYSQL_AUTHORIZE_RULES_PARAMS,
            flow_class=MySQLAuthorizeRulesFlows,
            flow_method="authorize_mysql_rules_v2",
            additional_mocks=additional_mocks,
        )

        # 不检查返回值是否为None，因为成功的流程方法可能返回None
        # 成功的验证依赖于EngineApiMock.last_result.result为True
