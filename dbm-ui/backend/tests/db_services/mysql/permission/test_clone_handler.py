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

import io
from collections import namedtuple
from unittest.mock import patch

import pytest
from django.core.cache import cache
from openpyxl.writer.excel import save_virtual_workbook

from backend.db_services.mysql.permission.clone.dataclass import CloneMeta
from backend.db_services.mysql.permission.clone.handlers import CloneHandler
from backend.db_services.mysql.permission.constants import CLONE_CLIENT_EXCEL_HEADER
from backend.tests.mock_data import constant
from backend.tests.mock_data.components.mysql_priv_manager import MySQLPrivManagerApiMock
from backend.tests.mock_data.db_services.mysql.permission.clone import (
    CLONE_CLIENT_LIST_DATA,
    EXCEL_CLONE_CLIENT_LIST_DATA,
)
from backend.utils.excel import ExcelHandler

pytestmark = pytest.mark.django_db


class TestCloneHandler:
    """
    CloneHandler的测试类
    """

    handler = CloneHandler(constant.BK_BIZ_ID, "admin", "client", "mysql")

    @patch("backend.db_services.mysql.permission.clone.handlers.MySQLPrivManagerApi", MySQLPrivManagerApiMock)
    def test_pre_check_clone(self):
        clone = CloneMeta(**CLONE_CLIENT_LIST_DATA)
        clone_result = cache.get(self.handler.pre_check_clone(clone)["clone_uid"])

        assert len(clone_result) == 3

    @patch("backend.db_services.mysql.permission.clone.handlers.MySQLPrivManagerApi", MySQLPrivManagerApiMock)
    def test_pre_check_excel_clone(self):
        data_dict__list = EXCEL_CLONE_CLIENT_LIST_DATA
        excel_bytes = save_virtual_workbook(ExcelHandler.serialize(data_dict__list, header=CLONE_CLIENT_EXCEL_HEADER))
        excel = io.BytesIO(excel_bytes)

        excel_obj = namedtuple("ExcelObj", ["file"])(file=excel)
        excel_clone = CloneMeta(clone_file=excel_obj, clone_type="client")

        clone_data_list = ExcelHandler.paser(excel_clone.clone_file.file)
        clone_keys = ["source", "target", "bk_cloud_id"]
        for index, clone_data in enumerate(clone_data_list):
            clone_data_list[index] = dict(zip(clone_keys, clone_data.values()))

        excel_clone.clone_list = clone_data_list
        clone_pre_check_data = self.handler.pre_check_excel_clone(excel_clone)
        assert clone_pre_check_data["pre_check"] is False

        clone_uid = clone_pre_check_data["clone_uid"]
        response = self.handler.get_clone_info_excel(clone=CloneMeta(clone_uid=clone_uid, clone_type="client"))
        assert response.content is not None
