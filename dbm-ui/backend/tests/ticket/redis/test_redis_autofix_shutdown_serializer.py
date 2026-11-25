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
from unittest.mock import patch

import pytest

from backend import env
from backend.configuration.constants import DBType
from backend.core.notify import handlers as notify_handlers
from backend.core.notify.constants import MsgType
from backend.db_services.redis.autofix.bill import build_failed_only_send_msg_config
from backend.ticket.builders.common import recycle as recycle_mod
from backend.ticket.builders.redis.redis_toolbox_autofix import RedisClusterAutofixDetailSerializer
from backend.ticket.builders.redis.redis_toolbox_instance_shutdown import RedisClusterInstShutdownDetailSerializer
from backend.ticket.constants import FlowType, TicketStatus, TicketType
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.models import Flow, Ticket


@pytest.mark.parametrize(
    "extra, expected",
    [
        ({}, False),
        ({"immediate_recycle": False}, False),
        ({"immediate_recycle": True}, True),
        ({"need_manual_confirm": False}, False),
    ],
    ids=["default-omitted", "explicit-false", "explicit-true", "no-confirm-does-not-enable-immediate"],
)
def test_autofix_detail_serializer_immediate_recycle(extra, expected):
    info = {
        "cluster_id": 1,
        "bk_cloud_id": 0,
        "proxy": [{"ip": "1.1.1.1", "spec_id": 1}],
        **extra,
    }
    serializer = RedisClusterAutofixDetailSerializer(
        data={"infos": [info]},
        context={"ticket_type": TicketType.REDIS_CLUSTER_AUTOFIX.value},
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["infos"][0]["immediate_recycle"] is expected


@pytest.mark.parametrize(
    "top_extra, info_extra, expected",
    [
        ({}, {}, False),
        ({"immediate_recycle": False}, {}, False),
        ({"immediate_recycle": True}, {}, True),
        ({}, {"need_manual_confirm": False}, False),
    ],
    ids=["default-omitted", "explicit-false", "explicit-true", "no-confirm-does-not-enable-immediate"],
)
def test_instance_shutdown_detail_serializer_immediate_recycle(top_extra, info_extra, expected):
    payload = {
        "infos": [
            {
                "cluster_id": 1,
                "redis_slave": ["2.2.2.2"],
                **info_extra,
            }
        ],
        **top_extra,
    }
    serializer = RedisClusterInstShutdownDetailSerializer(
        data=payload,
        context={"ticket_type": TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value},
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["immediate_recycle"] is expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    "shutdown_details_extra, expect_timer",
    [
        ({"immediate_recycle": True}, False),
        ({"immediate_recycle": False}, True),
        ({}, True),
    ],
    ids=["immediate-recycle-skips-timer", "explicit-false-keeps-timer", "omitted-keeps-timer"],
)
def test_instance_shutdown_derived_recycle_ticket_timer_behavior(monkeypatch, shutdown_details_extra, expect_timer):
    monkeypatch.setattr(env, "HOST_RECYCLE_RETENTION_DAYS", 7)
    monkeypatch.setattr(env, "SA_CHECK_TEMPLATE_ID", 0)
    monkeypatch.setattr(
        recycle_mod.BizSettings, "get_exact_hosting_biz", lambda *args, **kwargs: env.DBA_APP_BK_BIZ_ID
    )

    shutdown_ticket = Ticket.objects.create(
        group=DBType.Redis.value,
        creator="dba",
        updater="dba",
        bk_biz_id=3,
        ticket_type=TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value,
        remark="test shutdown",
        details={
            "infos": [{"cluster_id": 1, "redis_slave": ["1.1.1.1"], "need_manual_confirm": False}],
            **shutdown_details_extra,
        },
        config={},
    )
    recycle_hosts = [{"bk_host_id": 99001, "ip": "1.1.1.1", "bk_cloud_id": 0, "os_type": "Linux", "os_name": "tlinux"}]

    with patch.object(TicketFlowManager, "run_next_flow"), patch.object(
        recycle_mod.MachineEvent, "create_machine_events"
    ), patch("backend.configuration.models.dba.DBAdministrator.get_dba_for_db_type", return_value=(["dba"], [], [])):
        Ticket.create_recycle_ticket(shutdown_ticket.id, recycle_hosts, TicketType.RECYCLE_OLD_HOST)

    recycle_ticket = Ticket.objects.filter(ticket_type=TicketType.RECYCLE_OLD_HOST.value).order_by("-id").first()
    assert recycle_ticket is not None
    assert recycle_ticket.details["parent_ticket"] == shutdown_ticket.id
    assert recycle_ticket.details["immediate_recycle"] is (not expect_timer)

    flow_types = list(Flow.objects.filter(ticket=recycle_ticket).values_list("flow_type", flat=True))
    assert (FlowType.TIMER.value in flow_types) is expect_timer


def test_serializers_accept_optional_send_msg_config():
    msg_cfg = build_failed_only_send_msg_config()

    autofix_slz = RedisClusterAutofixDetailSerializer(
        data={
            "infos": [{"cluster_id": 1, "bk_cloud_id": 0, "proxy": [{"ip": "1.1.1.1", "spec_id": 1}]}],
            "send_msg_config": msg_cfg,
        },
        context={"ticket_type": TicketType.REDIS_CLUSTER_AUTOFIX.value},
    )
    assert autofix_slz.is_valid(), autofix_slz.errors
    assert autofix_slz.validated_data["send_msg_config"] == msg_cfg

    shutdown_slz = RedisClusterInstShutdownDetailSerializer(
        data={
            "infos": [{"cluster_id": 1, "redis_slave": ["2.2.2.2"]}],
            "immediate_recycle": True,
            "send_msg_config": msg_cfg,
        },
        context={"ticket_type": TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value},
    )
    assert shutdown_slz.is_valid(), shutdown_slz.errors
    assert shutdown_slz.validated_data["send_msg_config"] == msg_cfg


@pytest.mark.django_db
@pytest.mark.parametrize(
    "has_msg_config",
    [True, False],
    ids=["drill-failed-only-msg-config", "non-drill-default-msg-config"],
)
def test_instance_shutdown_derived_recycle_ticket_inherits_send_msg_config(monkeypatch, has_msg_config):
    monkeypatch.setattr(env, "HOST_RECYCLE_RETENTION_DAYS", 7)
    monkeypatch.setattr(env, "SA_CHECK_TEMPLATE_ID", 0)
    monkeypatch.setattr(
        recycle_mod.BizSettings, "get_exact_hosting_biz", lambda *args, **kwargs: env.DBA_APP_BK_BIZ_ID
    )

    msg_cfg = build_failed_only_send_msg_config() if has_msg_config else None
    shutdown_details = {
        "infos": [{"cluster_id": 1, "redis_slave": ["1.1.1.1"], "need_manual_confirm": not has_msg_config}],
        "immediate_recycle": has_msg_config,
    }
    if msg_cfg:
        shutdown_details["send_msg_config"] = msg_cfg

    shutdown_ticket = Ticket.objects.create(
        group=DBType.Redis.value,
        creator="dba",
        updater="dba",
        bk_biz_id=3,
        ticket_type=TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value,
        remark="test shutdown msg config",
        details=shutdown_details,
        config={"send_msg_config": msg_cfg or {}, "helpers": []},
    )
    recycle_hosts = [{"bk_host_id": 99002, "ip": "1.1.1.1", "bk_cloud_id": 0, "os_type": "Linux", "os_name": "tlinux"}]

    with patch.object(TicketFlowManager, "run_next_flow"), patch.object(
        recycle_mod.MachineEvent, "create_machine_events"
    ), patch("backend.configuration.models.dba.DBAdministrator.get_dba_for_db_type", return_value=(["dba"], [], [])):
        Ticket.create_recycle_ticket(shutdown_ticket.id, recycle_hosts, TicketType.RECYCLE_OLD_HOST)

    recycle_ticket = Ticket.objects.filter(ticket_type=TicketType.RECYCLE_OLD_HOST.value).order_by("-id").first()
    assert recycle_ticket is not None
    assert recycle_ticket.msg_config == (msg_cfg or {})


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status, expect_sent",
    [
        (TicketStatus.APPROVE.value, False),
        (TicketStatus.TODO.value, True),
        (TicketStatus.RUNNING.value, False),
        (TicketStatus.SUCCEEDED.value, False),
        (TicketStatus.TERMINATED.value, False),
        (TicketStatus.FAILED.value, True),
    ],
    ids=[
        "approve-suppressed",
        "todo-sends-rtx",
        "inner-todo-suppressed",
        "succeeded-suppressed",
        "terminated-suppressed",
        "failed-sends-rtx",
    ],
)
def test_failed_only_send_msg_config_notify_adapter_behavior(monkeypatch, status, expect_sent):
    msg_cfg = build_failed_only_send_msg_config()
    ticket = Ticket.objects.create(
        group=DBType.Redis.value,
        creator="dba",
        updater="dba",
        bk_biz_id=3,
        ticket_type=TicketType.REDIS_CLUSTER_AUTOFIX.value,
        status=status,
        remark="test drill notify",
        details={},
        config={"send_msg_config": msg_cfg, "helpers": []},
    )

    sent_calls = []

    class _FakeNotifyHandler:
        def __init__(self, title, content, receivers):
            self.title = title
            self.content = content
            self.receivers = receivers

        @classmethod
        def get_msg_type(cls):
            return [MsgType.RTX.value]

        def send_msg(self, msg_type, context=None):
            sent_calls.append((msg_type, self.receivers))

    # 即使业务默认对所有阶段开启 rtx，单据级 failed-only 配置仍应优先抑制非失败阶段
    monkeypatch.setattr(
        notify_handlers.BizSettings,
        "get_setting_value",
        staticmethod(lambda *args, **kwargs: {s: {MsgType.RTX.value: True} for s in TicketStatus.get_values()}),
    )
    monkeypatch.setattr(notify_handlers.NotifyAdapter, "get_receivers", lambda self: ["dba"])
    monkeypatch.setattr(
        notify_handlers.NotifyAdapter, "get_notify_class", lambda self, msg_type: (_FakeNotifyHandler, {})
    )
    monkeypatch.setattr(
        notify_handlers.NotifyAdapter, "render_msg_template", lambda self, msg_type: ("title", "content")
    )

    notify_handlers.NotifyAdapter(ticket.id).send_msg()

    if expect_sent:
        assert sent_calls == [(MsgType.RTX.value, ["dba"])]
    else:
        assert sent_calls == []
