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
from dataclasses import asdict
from typing import List, Type

import pytest
from django.test import TestCase
from pipeline.component_framework.component import Component

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.flow.consts import DnsOpType
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.mysql.mysql_act_dataclass import CreateDnsKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import SingleApplyAutoContext
from backend.tests.flow.components.collections.mysql.utils import MySQLSingleApplyComponentTest
from backend.tests.mock_data.components import cc

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


class TestMySQLDnsManageComponent(MySQLSingleApplyComponentTest, TestCase):
    def component_cls(self) -> Type[Component]:
        return MySQLDnsManageComponent

    def to_mock_path_list(self) -> List[str]:
        mock_path_list = super().to_mock_path_list()
        mock_path_list.append(DnsManage.__module__)
        return mock_path_list

    @classmethod
    def _set_trans_data(cls) -> None:
        cls.trans_data = SingleApplyAutoContext(new_ip=cc.NORMAL_IP)

    @classmethod
    def _set_kwargs(cls) -> None:
        super()._set_kwargs()
        dns_kwargs = CreateDnsKwargs(
            bk_cloud_id=DEFAULT_BK_CLOUD_ID,
            dns_op_type=DnsOpType.CREATE,
            add_domain_name=cls.global_data["clusters"][0]["master"],
            dns_op_exec_port=cls.global_data["clusters"][0]["mysql_port"],
        )
        cls.kwargs.update(asdict(dns_kwargs))

    @classmethod
    def _set_excepted_outputs(cls) -> None:
        cls.excepted_outputs = {}
