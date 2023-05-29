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
from mock import patch

from backend import env
from backend.db_services.mysql.sql_import.dataclass import SQLMeta
from backend.db_services.mysql.sql_import.handlers import SQLHandler
from backend.tests.mock_data import constant
from backend.tests.mock_data.components.sql_import import SQLImportApiMock
from backend.tests.mock_data.components.storage import get_storage_mock

pytestmark = pytest.mark.django_db


class TestSQLImportHandler:
    """
    SQL导入的handler测试类
    """

    handler = SQLHandler(bk_biz_id=constant.BK_BIZ_ID)

    @patch("backend.db_services.mysql.sql_import.handlers.get_storage", get_storage_mock)
    @patch("backend.db_services.mysql.sql_import.handlers.SQLImportApi", SQLImportApiMock)
    def test_grammar_check(self):
        sql_content = "select * from user"
        sql = SQLMeta(sql_content=sql_content)
        check_info = self.handler.grammar_check(sql)

        assert len(check_info) == 1
