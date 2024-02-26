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
import uuid
from unittest.mock import PropertyMock, patch

import pytest
from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from backend.db_meta.models.db_module import DBModule
from backend.flow.models import FlowNode, FlowTree
from backend.tests.mock_data.components.bamboo_engine import BambooEngineMock
from backend.tests.mock_data.components.cc import CCApiMock
from backend.tests.mock_data.components.dbconfig import DBConfigApiMock
from backend.tests.mock_data.components.itsm import ItsmApiMock
from backend.tests.mock_data.iam_app.permission import PermissionMock
from backend.tests.mock_data.ticket.ticket_flow import (
    APPLY_RESOURCE_RETURN_DATA,
    DB_MODULE_DATA,
    FLOW_TREE_DATA,
    MYSQL_AUTHORIZE_TICKET_DATA,
    MYSQL_ITSM_AUTHORIZE_TICKET_DATA,
    MYSQL_PERMISSION_ACCOUNT,
    MYSQL_SINGLE_APPLY_TICKET_DATA,
    MYSQL_TENDBHA_TICKET_DATA,
    ROOT_ID,
    SN,
    SQL_IMPORT_FLOW_NODE_DATA,
    SQL_IMPORT_TICKET_DATA,
)
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketStatus
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.flow_manager.pause import PauseFlow
from backend.ticket.models import Flow
from backend.ticket.views import TicketViewSet

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db
client = APIClient()

INITIAL_FLOW_FINISHED_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.SUCCEEDED]
CHANGED_MOCK_STATUS = [TicketFlowStatus.SKIPPED, TicketStatus.SUCCEEDED, TicketFlowStatus.RUNNING]


@pytest.fixture(scope="module")
def query_fixture(django_db_blocker):
    with django_db_blocker.unblock():
        DBModule.objects.create(**DB_MODULE_DATA)
        FlowTree.objects.create(**FLOW_TREE_DATA)
        FlowNode.objects.create(**SQL_IMPORT_FLOW_NODE_DATA)

        yield
        DBModule.objects.all().delete()
        FlowTree.objects.all().delete()
        FlowNode.objects.all().delete()


@pytest.fixture(autouse=True)  # autouse=True 会自动应用这个fixture到所有的测试中
def set_empty_middleware():
    with patch.object(settings, "MIDDLEWARE", []):
        yield


class TestTicketFlow:
    """
    测试mysql授权流程正确性
    """

    # 某个对象的某个属性替换为一个模拟对象,模拟TicketViewSet和InnerFlow类的属性和方法
    @patch.object(TicketViewSet, "permission_classes")
    @patch.object(InnerFlow, "_run")
    @patch.object(InnerFlow, "status", new_callable=PropertyMock)
    @patch.object(TicketViewSet, "get_permissions", lambda x: [])
    @patch("backend.ticket.flow_manager.itsm.ItsmApi", ItsmApiMock())
    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    @patch(
        "backend.db_services.mysql.permission.db_account.handlers.MySQLPrivManagerApi.list_account_rules",
        return_value=MYSQL_PERMISSION_ACCOUNT,
    )
    def test_authorize_ticket_flow(
        self, mocked_list_account_rules, mocked_status, mocked__run, mocked_permission_classes, db
    ):
        # 测试单据流程：start --> inner --> end
        mocked_status.return_value = TicketStatus.SUCCEEDED
        mocked__run.return_value = ROOT_ID
        mocked_permission_classes.return_value = [AllowAny]

        client.login(username="admin")
        authorize_uid = uuid.uuid1().hex
        cache.set(authorize_uid, MYSQL_ITSM_AUTHORIZE_TICKET_DATA)
        authorize_data = copy.deepcopy(MYSQL_AUTHORIZE_TICKET_DATA)
        authorize_data["details"]["authorize_uid"] = authorize_uid

        client.post("/apis/tickets/", data=authorize_data)
        flow_data = Flow.objects.exclude(flow_obj_id="").last()
        assert flow_data.flow_obj_id is not None

        cache.delete(authorize_uid)

    @patch.object(TicketViewSet, "permission_classes")
    @patch.object(InnerFlow, "_run")
    @patch.object(InnerFlow, "status", new_callable=PropertyMock)
    @patch.object(TicketViewSet, "get_permissions", lambda x: [])
    @patch("backend.ticket.flow_manager.itsm.ItsmApi", ItsmApiMock())
    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    @patch("backend.components.cmsi.handler.CmsiHandler.send_msg", lambda msg: "有一条MySQL 高可用部署待办需要您处理")
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    @patch("backend.ticket.builders.mysql.mysql_single_apply.DBConfigApi", DBConfigApiMock)
    def test_mysql_single_apply_flow(self, mocked_status, mocked__run, mocked_permission_classes, query_fixture, db):
        # 测试流程单据: start --> itsm --> PAUSE --> end
        mocked_status.return_value = TicketStatus.SUCCEEDED
        mocked__run.return_value = ROOT_ID
        mocked_permission_classes.return_value = [AllowAny]

        client.login(username="admin")

        # itsm流程
        single_apply_data = copy.deepcopy(MYSQL_SINGLE_APPLY_TICKET_DATA)
        client.post("/apis/tickets/", data=single_apply_data)
        current_flow = Flow.objects.filter(flow_obj_id=SN).first()
        assert current_flow is not None

        # inner流程
        client.post(f"/apis/tickets/{current_flow.ticket_id}/callback/")
        current_flow = Flow.objects.exclude(flow_obj_id="").last()
        assert current_flow.flow_type == FlowType.PAUSE

    @patch.object(TicketViewSet, "permission_classes")
    @patch.object(InnerFlow, "_run")
    @patch.object(InnerFlow, "status", new_callable=PropertyMock)
    @patch.object(TicketViewSet, "get_permissions", lambda x: [])
    @patch("backend.ticket.builders.mysql.mysql_import_sqlfile.BambooEngine", BambooEngineMock)
    @patch("backend.ticket.flow_manager.itsm.ItsmApi", ItsmApiMock())
    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    def test_sql_import_flow(self, mocked_status, mocked__run, mocked_permission_classes, query_fixture, db):
        # 测试流程：start --> itsm --> inner --> end
        mocked_status.return_value = TicketStatus.SUCCEEDED
        mocked__run.return_value = ROOT_ID
        mocked_permission_classes.return_value = [AllowAny]

        client.login(username="admin")

        # 语义检查流程 & itsm
        sql_import_data = copy.deepcopy(SQL_IMPORT_TICKET_DATA)
        client.post("/apis/tickets/", data=sql_import_data)
        current_flow = Flow.objects.exclude(flow_obj_id="").last()
        assert current_flow.flow_type == FlowType.BK_ITSM

        # inner流程
        client.post(f"/apis/tickets/{current_flow.ticket_id}/callback/")
        current_flow = Flow.objects.exclude(flow_obj_id="").last()
        assert current_flow.flow_type == FlowType.INNER_FLOW

    @patch.object(TicketViewSet, "permission_classes")
    @patch.object(InnerFlow, "_run")
    @patch.object(InnerFlow, "status", new_callable=PropertyMock)
    @patch.object(PauseFlow, "status", new_callable=PropertyMock)
    @patch.object(TicketViewSet, "get_permissions", lambda x: [])
    @patch("backend.ticket.flow_manager.itsm.ItsmApi", ItsmApiMock())
    @patch("backend.db_services.cmdb.biz.CCApi", CCApiMock())
    @patch("backend.components.cmsi.handler.CmsiHandler.send_msg", lambda msg: "有一条MySQL 高可用部署待办需要您处理")
    @patch(
        "backend.ticket.flow_manager.resource.ResourceApplyFlow.apply_resource",
        lambda resource_request_id, node_infos: (1, APPLY_RESOURCE_RETURN_DATA),
    )
    @patch(
        "backend.ticket.flow_manager.resource.ResourceApplyFlow.patch_resource_params", lambda self, ticket_data: None
    )
    @patch("backend.db_services.cmdb.biz.Permission", PermissionMock)
    @patch("backend.ticket.builders.mysql.mysql_ha_apply.DBConfigApi", DBConfigApiMock)
    def test_mysql_HA_apply_flow(
        self, mock_pause_status, mocked_status, mocked__run, mocked_permission_classes, query_fixture, db
    ):
        # MySQL 高可用部署: start --> itsm --> PAUSE --> RESOURC --> INNER_FLOW --> end
        mocked_status.return_value = TicketStatus.SUCCEEDED
        mock_pause_status.return_value = TicketFlowStatus.SKIPPED
        mocked__run.return_value = ROOT_ID
        mocked_permission_classes.return_value = [AllowAny]

        client.login(username="admin")

        # itsm流程
        tendbha_apply_data = copy.deepcopy(MYSQL_TENDBHA_TICKET_DATA)
        client.post("/apis/tickets/", data=tendbha_apply_data)
        current_flow = Flow.objects.filter(flow_obj_id=SN).first()
        assert current_flow is not None

        # PAUSE流程
        client.post(f"/apis/tickets/{current_flow.ticket_id}/callback/")
        current_flow = Flow.objects.exclude(flow_obj_id="").last()
        assert current_flow.flow_type == FlowType.PAUSE
        # RESOURCE_APPLY -> INNER_FLOW
        client.post(f"/apis/tickets/{current_flow.ticket_id}/callback/")
        current_flow = Flow.objects.exclude(flow_obj_id="").last()
        assert current_flow.flow_type == FlowType.INNER_FLOW
