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
from openpyxl.writer.excel import save_virtual_workbook

from backend.db_services.mysql.permission.authorize.dataclass import MySQLAuthorizeMeta, MySQLExcelAuthorizeMeta
from backend.db_services.mysql.permission.authorize.handlers import MySQLAuthorizeHandler
from backend.db_services.mysql.permission.constants import AUTHORIZE_EXCEL_HEADER
from backend.tests.mock_data import constant
from backend.tests.mock_data.components.mysql_priv_manager import DBPrivManagerApiMock
from backend.tests.mock_data.db_services.mysql.permission.authorize import AUTHORIZE_DATA, EXCEL_DATA_DICT__LIST
from backend.utils.excel import ExcelHandler

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def query_fixture(django_db_blocker):
    pass


class TestAuthorizeHandler:
    """
    AuthorizeHandler的测试类
    """

    handler = MySQLAuthorizeHandler(bk_biz_id=constant.BK_BIZ_ID)

    @patch("backend.db_services.mysql.permission.authorize.handlers.DBPrivManagerApi", DBPrivManagerApiMock)
    def test_pre_check_rules(self, query_fixture):
        authorize = MySQLAuthorizeMeta(**AUTHORIZE_DATA)
        authorize_result = self.handler.pre_check_rules(authorize)
        assert authorize_result["pre_check"] is True

    @patch("backend.db_services.mysql.permission.authorize.handlers.DBPrivManagerApi", DBPrivManagerApiMock)
    def test_pre_check_excel_rules(self, query_fixture):
        data_dict__list = EXCEL_DATA_DICT__LIST
        excel_bytes = save_virtual_workbook(ExcelHandler.serialize(data_dict__list, headers=AUTHORIZE_EXCEL_HEADER))
        excel = io.BytesIO(excel_bytes)

        excel_obj = namedtuple("ExcelObj", ["file"])(file=excel)
        excel_authorize = MySQLExcelAuthorizeMeta(authorize_file=excel_obj)
        excel_authorize.authorize_excel_data = ExcelHandler.paser(excel_authorize.authorize_file.file)

        authorize_data_list = self.handler.pre_check_excel_rules(excel_authorize)
        assert authorize_data_list["pre_check"] is True
