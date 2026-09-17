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
from unittest.mock import MagicMock, patch

from backend.dbm_aiagent.mcp_tools.mysql.impl import ticket_dedup
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup import find_duplicate_ticket
from backend.ticket.constants import TicketStatus

MODULE = "backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_dedup"


def _candidates(mock_ticket, items):
    """让 Ticket.objects.filter(...).order_by(...) 返回可迭代的候选列表"""
    qs = mock_ticket.objects.filter.return_value.order_by.return_value
    qs.__iter__.return_value = iter(items)
    return qs


class TestDedupActiveStatuses:
    """幂等去重活跃状态集合：排除 FAILED，允许失败后快速重试"""

    def test_excludes_failed(self):
        assert TicketStatus.FAILED not in ticket_dedup.DEDUP_ACTIVE_STATUSES

    def test_includes_pending_and_running(self):
        assert TicketStatus.PENDING in ticket_dedup.DEDUP_ACTIVE_STATUSES
        assert TicketStatus.RUNNING in ticket_dedup.DEDUP_ACTIVE_STATUSES
        assert TicketStatus.APPROVE in ticket_dedup.DEDUP_ACTIVE_STATUSES
        assert TicketStatus.TODO in ticket_dedup.DEDUP_ACTIVE_STATUSES


class TestFindDuplicateTicket:
    """find_duplicate_ticket：命中复用 / 未命中 / 异常跳过 / 过滤参数"""

    @patch(f"{MODULE}.Ticket")
    def test_hit_returns_existing(self, mock_ticket):
        existing = MagicMock()
        existing.pk = 123
        _candidates(mock_ticket, [existing])

        result = find_duplicate_ticket(
            ticket_type="T1",
            creator="u1",
            bk_biz_id=1,
            target_fingerprint=("a", "b"),
            fingerprint_of=lambda tk: ("a", "b"),
        )
        assert result is existing

    @patch(f"{MODULE}.Ticket")
    def test_miss_returns_none(self, mock_ticket):
        other = MagicMock()
        _candidates(mock_ticket, [other])

        result = find_duplicate_ticket(
            ticket_type="T1",
            creator="u1",
            bk_biz_id=1,
            target_fingerprint=("a", "b"),
            fingerprint_of=lambda tk: ("a", "c"),
        )
        assert result is None

    @patch(f"{MODULE}.Ticket")
    def test_fingerprint_exception_skips(self, mock_ticket):
        bad = MagicMock()
        good = MagicMock()
        _candidates(mock_ticket, [bad, good])

        def fingerprint_of(tk):
            if tk is bad:
                raise ValueError("bad details")
            return ("a", "b")

        result = find_duplicate_ticket(
            ticket_type="T1",
            creator="u1",
            bk_biz_id=1,
            target_fingerprint=("a", "b"),
            fingerprint_of=fingerprint_of,
        )
        assert result is good

    @patch(f"{MODULE}.Ticket")
    def test_filter_uses_active_statuses_and_window(self, mock_ticket):
        _candidates(mock_ticket, [])

        find_duplicate_ticket(
            ticket_type="T1",
            creator="u1",
            bk_biz_id=1,
            target_fingerprint=("a",),
            fingerprint_of=lambda tk: ("a",),
        )

        kwargs = mock_ticket.objects.filter.call_args.kwargs
        assert kwargs["ticket_type"] == "T1"
        assert kwargs["creator"] == "u1"
        assert kwargs["bk_biz_id"] == 1
        assert TicketStatus.FAILED not in kwargs["status__in"]
        assert kwargs["create_at__gte"] is not None
