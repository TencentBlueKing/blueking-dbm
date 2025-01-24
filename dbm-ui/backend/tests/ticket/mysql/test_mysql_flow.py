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
import copy
import logging
import os
import uuid
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache

from backend.flow.models import FlowNode, FlowTree
from backend.tests.mock_data.components.dbconfig import DBConfigApiMock
from backend.tests.mock_data.components.mysql_priv_manager import DBPrivManagerApiMock
from backend.tests.mock_data.components.sql_import import SQLSimulationApiMock
from backend.tests.mock_data.flow.engine.bamboo.engine import BambooEngineMock
from backend.tests.mock_data.ticket.mysql_flow import (
    MYSQL_AUTHORIZE_TICKET_DATA,
    MYSQL_ITSM_AUTHORIZE_TICKET_DATA,
    MYSQL_SINGLE_APPLY_TICKET_DATA,
    MYSQL_TENDBHA_TICKET_DATA,
    SQL_IMPORT_FLOW_NODE_DATA,
    SQL_IMPORT_TICKET_DATA,
)
from backend.tests.mock_data.ticket.ticket_flow import FLOW_TREE_DATA
from backend.tests.ticket.server_base import BaseTicketTest
from backend.ticket.constants import EXCLUSIVE_TICKET_EXCEL_PATH, TicketType
from backend.utils.excel import ExcelHandler

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_mysql_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        FlowTree.objects.create(**FLOW_TREE_DATA)
        FlowNode.objects.create(**SQL_IMPORT_FLOW_NODE_DATA)
        yield
        FlowTree.objects.all().delete()
        FlowNode.objects.all().delete()


class TestMySQLTicket(BaseTicketTest):
    """
    测试mysql授权流程正确性
    """

    @classmethod
    def apply_patches(cls):
        mock_list_account_rules_patch = patch(
            "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi", DBPrivManagerApiMock
        )
        mock_dbconfig_api_patch = patch(
            "backend.ticket.builders.mysql.mysql_single_apply.DBConfigApi", DBConfigApiMock
        )
        mock_simulation_api_patch = patch(
            "backend.ticket.builders.mysql.mysql_import_sqlfile.SQLSimulationApi", SQLSimulationApiMock
        )
        mock_bamboo_api_patch = patch(
            "backend.ticket.builders.mysql.mysql_import_sqlfile.BambooEngine", BambooEngineMock
        )
        cls.patches.extend(
            [
                mock_list_account_rules_patch,
                mock_dbconfig_api_patch,
                mock_simulation_api_patch,
                mock_bamboo_api_patch,
            ]
        )
        super().apply_patches()

    def test_mysql_authorize_ticket_flow(self):
        authorize_uid = uuid.uuid1().hex
        cache.set(authorize_uid, MYSQL_ITSM_AUTHORIZE_TICKET_DATA)
        authorize_data = copy.deepcopy(MYSQL_AUTHORIZE_TICKET_DATA)
        authorize_data["details"]["authorize_uid"] = authorize_uid
        self.flow_test(authorize_data)
        cache.delete(authorize_uid)

    def test_mysql_single_apply_flow(self):
        self.flow_test(MYSQL_SINGLE_APPLY_TICKET_DATA)

    def test_mysql_sql_import_flow(self):
        self.flow_test(SQL_IMPORT_TICKET_DATA)

    def test_mysql_ha_apply_flow(self):
        self.flow_test(MYSQL_TENDBHA_TICKET_DATA)

    def test_exclusive_ticket_map(self):
        # 测试互斥表互斥逻辑正常
        path = os.path.join(settings.BASE_DIR, EXCLUSIVE_TICKET_EXCEL_PATH)
        exclusive_matrix = ExcelHandler.paser_matrix(path)
        invalid_labels = set(exclusive_matrix.keys()) - set(TicketType.get_labels())
        logger.warning("invalid_labels is %s", invalid_labels)
        assert len(invalid_labels) == 0
