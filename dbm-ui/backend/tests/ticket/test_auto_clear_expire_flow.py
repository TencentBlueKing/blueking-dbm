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

import pytest
from django.db import connection

from backend.tests.mock_data.ticket.ticket_flow import FLOW_DATA, TICKET_CONFIG_DATA, TICKET_DATA, TODO_DATA
from backend.ticket.constants import TicketStatus
from backend.ticket.models import Flow, Ticket, TicketFlowsConfig, Todo
from backend.ticket.tasks.ticket_tasks import TicketTask

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def query_fixture(django_db_blocker):
    with django_db_blocker.unblock():
        ticket = Ticket.objects.create(**TICKET_DATA)
        with connection.cursor() as cursor:
            cursor.execute("UPDATE ticket_ticket SET update_at = %s WHERE id = %s", ["2025-06-28 10:05:48", 585])
        FLOW_DATA[0]["ticket"] = ticket
        FLOW_DATA[1]["ticket"] = ticket
        FLOW_DATA[2]["ticket"] = ticket
        FLOW_DATA[3]["ticket"] = ticket
        flows = Flow.objects.bulk_create([Flow(**data) for data in FLOW_DATA])
        TODO_DATA[0]["ticket"] = ticket
        TODO_DATA[0]["flow"] = flows[0]
        TODO_DATA[1]["ticket"] = ticket
        TODO_DATA[1]["flow"] = flows[1]
        Todo.objects.bulk_create([Todo(**data) for data in TODO_DATA])
        tk_config = TicketFlowsConfig.objects.get(ticket_type=TICKET_DATA["ticket_type"])
        tk_config.configs = TICKET_CONFIG_DATA
        tk_config.save()
        yield
        Todo.objects.all().delete()
        Flow.objects.all().delete()
        Ticket.objects.all().delete()


class TestAutoClearExpireFlow(object):
    def test_auto_clear_expire_flow(self, query_fixture, db):
        TicketTask.auto_clear_expire_flow()
        revoke_ticket = Ticket.objects.get(id=TICKET_DATA["id"])
        assert revoke_ticket.status == TicketStatus.TERMINATED
