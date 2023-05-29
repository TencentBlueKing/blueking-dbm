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
from dataclasses import asdict
from typing import Type

import pytest
from django.test import TestCase
from pipeline.component_framework.component import Component

from backend import env
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs
from backend.flow.utils.mysql.mysql_context_dataclass import SingleApplyAutoContext
from backend.tests.flow.components.collections.mysql.utils import MySQLSingleApplyComponentTest
from backend.tests.mock_data.components import cc
from backend.tests.mock_data.components.job import JOB_INSTANCE_ID, STEP_INSTANCE_ID

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


class TestTransFileComponent(MySQLSingleApplyComponentTest, TestCase):
    def component_cls(self) -> Type[Component]:
        return TransFileComponent

    @classmethod
    def _set_trans_data(cls) -> None:
        cls.trans_data = SingleApplyAutoContext(new_ip=cc.NORMAL_IP)

    @classmethod
    def _set_kwargs(cls):
        trans_files = GetFileList()
        act_kwargs = DownloadMediaKwargs(
            bk_cloud_id=0,
            file_list=trans_files.mysql_install_package(db_version=cls.global_data["db_version"]),
            exec_ip="1.1.1.1",
        )
        cls.kwargs = asdict(act_kwargs)
        cls.kwargs.update({"root_id": uuid.uuid1().hex, "node_id": uuid.uuid1().hex, "node_name": "Component"})

    @classmethod
    def _set_excepted_outputs(cls) -> None:
        cls.excepted_outputs = {
            "ext_result": {
                "result": True,
                "code": 0,
                "message": "success",
                "data": {
                    "job_instance_name": f"API Quick Distribution{env.JOB_BLUEKING_BIZ_ID}",
                    "job_instance_id": JOB_INSTANCE_ID,
                    "step_instance_id": STEP_INSTANCE_ID,
                },
            }
        }
