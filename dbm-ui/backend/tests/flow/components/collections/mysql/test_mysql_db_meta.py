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

from backend.constants import DEFAULT_TIME_ZONE
from backend.db_meta.api.cluster.tendbsingle.create_cluster import create as tendbsingle_create
from backend.db_meta.api.common.common import add_service_instance
from backend.db_meta.api.machine.apis import create as api_create
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import SingleApplyAutoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.tests.flow.components.collections.base import BaseComponentPatcher as Patcher
from backend.tests.flow.components.collections.mysql.utils import MySQLSingleApplyComponentTest
from backend.tests.mock_data.components import cc
from backend.ticket.constants import TicketType

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("create_city", "init_db_module")
class TestMySQLDBMetaComponent(MySQLSingleApplyComponentTest, TestCase):
    def component_cls(self) -> Type[Component]:
        return MySQLDBMetaComponent

    def to_mock_path_list(self) -> List[str]:
        mock_path_list = super().to_mock_path_list()
        mock_path_list.extend(
            [
                MySQLDBMeta.__module__,
                api_create.__module__,
                tendbsingle_create.__module__,
                add_service_instance.__module__,
            ]
        )
        return mock_path_list

    def get_patchers(self) -> List[Patcher]:
        patchers = super(TestMySQLDBMetaComponent, self).get_patchers()
        # TODO: 临时方案，直接mock掉TenDBSingleClusterHandler.create
        # TODO: 待解决 ---> 为什么这个Patcher对模块中的方法不生效
        patchers.append(
            Patcher(
                target="backend.db_meta.api.cluster.tendbsingle.handler.TenDBSingleClusterHandler.create",
                return_value=None,
            )
        )
        return patchers

    @classmethod
    def _set_trans_data(cls) -> None:
        cls.trans_data = SingleApplyAutoContext(new_ip=cc.NORMAL_IP, time_zone_info={"time_zone": DEFAULT_TIME_ZONE})

    @classmethod
    def _set_kwargs(cls) -> None:
        super()._set_kwargs()
        db_meta_kwargs = DBMetaOPKwargs(
            db_meta_class_func=TicketType.MYSQL_SINGLE_APPLY.value.lower(),
            is_update_trans_data=True,
        )
        cls.kwargs.update(asdict(db_meta_kwargs))

    @classmethod
    def _set_excepted_outputs(cls) -> None:
        cls.excepted_outputs = {"ext_result": True}
