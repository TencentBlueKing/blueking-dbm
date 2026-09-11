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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.db_services.mongodb.autofix.gates import RESTART_SHIELD_TICKET_TYPES
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import create_mongod_ensure_start_ticket
from backend.ticket.constants import TicketType


def test_ensure_start_in_restart_shield_types():
    assert TicketType.MONGODB_INSTANCE_ENSURE_START.value in RESTART_SHIELD_TICKET_TYPES


def test_create_mongod_ensure_start_ticket_details():
    cluster = SimpleNamespace(id=11, major_version="mongodb-6.0", immute_domain="m1.test.dba.db")
    machine = SimpleNamespace(bk_host_id=1001, ip="127.0.0.1", bk_cloud_id=0)
    storage = SimpleNamespace(id=501, port=27017, machine_type="mongodb", machine=machine)
    storage.cluster = MagicMock()
    storage.cluster.first.return_value = cluster

    core = SimpleNamespace(
        id=42,
        bk_biz_id=3,
        ip="127.0.0.1",
        bk_host_id=1001,
        ports=[27017],
        cluster_id=11,
        immute_domain="m1.test.dba.db",
        pre_ticket_id=0,
    )
    created = SimpleNamespace(id=9001)

    qs = MagicMock()
    qs.select_related.return_value = qs
    qs.prefetch_related.return_value = qs
    qs.filter.return_value = qs
    qs.first.return_value = storage

    with (
        patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket.StorageInstance.objects",
            qs,
        ),
        patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket._apply_followup_approval_flags",
            side_effect=lambda d: d.update(need_itsm=True, need_manual_confirm=True) or d,
        ),
        patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket.Ticket.create_ticket",
            return_value=created,
        ) as create_ticket,
        patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket.notify.send_msg.apply_async",
        ),
    ):
        ticket = create_mongod_ensure_start_ticket(core, creator="admin")

    assert ticket is created
    kwargs = create_ticket.call_args.kwargs
    assert kwargs["ticket_type"] == TicketType.MONGODB_INSTANCE_ENSURE_START.value
    assert "自愈#42" in kwargs["remark"] or "自愈#42" in str(kwargs["remark"])
    assert kwargs["details"]["need_itsm"] is True
    assert kwargs["details"]["infos"][0]["ip"] == "127.0.0.1"
    assert kwargs["details"]["infos"][0]["port"] == 27017
    assert kwargs["details"]["infos"][0]["cluster_id"] == 11
