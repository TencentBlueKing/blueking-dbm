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
from typing import Type

import mock
import pytest
from django.test import TestCase
from pipeline.component_framework.component import Component

from backend import env
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums import ClusterType
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SingleApplyAutoContext
from backend.tests.flow.components.collections.mysql.utils import MySQLSingleApplyComponentTest
from backend.tests.mock_data.components import cc
from backend.tests.mock_data.components.dbconfig import DBConfigApiMock
from backend.tests.mock_data.components.job import JOB_INSTANCE_ID, STEP_INSTANCE_ID

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


class TestExecActuatorScriptComponent(MySQLSingleApplyComponentTest, TestCase):
    def component_cls(self) -> Type[Component]:
        with mock.patch(target="backend.flow.utils.mysql.mysql_act_playload.DBConfigApi", new=DBConfigApiMock):
            return ExecuteDBActuatorScriptComponent

    def to_mock_path_list(self):
        path_list = super(TestExecActuatorScriptComponent, self).to_mock_path_list()
        path_list.append(MysqlActPayload.__module__)
        return path_list

    @classmethod
    def _set_trans_data(cls) -> None:
        with mock.patch(target="backend.flow.utils.mysql.mysql_act_playload.DBConfigApi", new=DBConfigApiMock):
            cls.trans_data = SingleApplyAutoContext(new_ip=cc.NORMAL_IP)

    @classmethod
    def _set_kwargs(cls) -> None:
        super()._set_kwargs()
        cls.kwargs.update(
            {
                "get_mysql_payload_func": MysqlActPayload.get_sys_init_payload.__name__,
                "cluster": {"new_ip": cc.NORMAL_IP},
                "cluster_type": ClusterType.TenDBSingle,
                "bk_cloud_id": DEFAULT_BK_CLOUD_ID,
            }
        )

    @classmethod
    def _set_excepted_outputs(cls) -> None:
        cls.excepted_outputs = {
            "ext_result": {
                "result": True,
                "code": 0,
                "message": "success",
                "data": {
                    "job_instance_name": f"API Quick execution script{env.JOB_BLUEKING_BIZ_ID}",
                    "job_instance_id": JOB_INSTANCE_ID,
                    "step_instance_id": STEP_INSTANCE_ID,
                },
            },
            "exec_ips": ["127.0.0.1"],
        }
