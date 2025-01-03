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
from typing import Any, List, NoReturn, Type, Union

import pytest
from django.test import TestCase
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.mysql.authorize_rules_v2 import AuthorizeRulesV2Component
from backend.tests.flow.components.collections.base import BaseComponentPatcher as Patcher
from backend.tests.flow.components.collections.mysql.utils import MySQLComponentBaseTest
from backend.tests.mock_data.components.mysql_priv_manager import DBPrivManagerApiMock
from backend.tests.mock_data.ticket.ticket_params_data import MYSQL_AUTHORIZE_FLOW_PARAMS

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


class TestAuthorizeRulesComponent(MySQLComponentBaseTest, TestCase):
    @classmethod
    def _set_kwargs(cls) -> None:
        cls.kwargs = MYSQL_AUTHORIZE_FLOW_PARAMS

    @classmethod
    def _set_excepted_outputs(cls) -> None:
        cls.excepted_outputs = {}

    def component_cls(self) -> Type[Component]:
        return AuthorizeRulesV2Component

    def tearDown(self) -> Union[Any, NoReturn]:
        pass

    def get_patchers(self) -> List[Patcher]:
        patchers = super().get_patchers()
        patchers.append(
            Patcher(
                target="backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi",
                new=DBPrivManagerApiMock,
            )
        )
        return patchers
