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
from datetime import timedelta
from typing import Callable, Optional

from django.utils import timezone

from backend.ticket.constants import TICKET_TODO_STATUS_SET, TicketStatus
from backend.ticket.models import Ticket

# LLM 超时重试 / 多轮对话导致的重复提单时间窗口（分钟）
DEDUP_WINDOW_MINUTES = 5

# 未完结状态：PENDING（刚创建未进入流程）+ TODO 相关状态（审批/待执行/补货/执行中/定时中）。
# 注意：排除 FAILED，失败单据应允许在时间窗口内重新提单，避免被幂等误复用。
DEDUP_ACTIVE_STATUSES = [TicketStatus.PENDING] + [
    status for status in TICKET_TODO_STATUS_SET if status != TicketStatus.FAILED
]


def find_duplicate_ticket(
    ticket_type: str,
    creator: str,
    bk_biz_id: int,
    target_fingerprint,
    fingerprint_of: Callable[[Ticket], object],
) -> Optional[Ticket]:
    """
    幂等防重：在时间窗口内，查找「同一 ticket_type + creator + 业务 + 相同目标」的未完结单据。

    - target_fingerprint：本次操作的目标指纹（可哈希对象，如排序后的 tuple）
    - fingerprint_of：从历史 Ticket 提取目标指纹的函数（要求与 target_fingerprint 同构）
    命中则返回已存在单据（幂等复用），否则返回 None。
    """
    window_start = timezone.now() - timedelta(minutes=DEDUP_WINDOW_MINUTES)

    candidates = Ticket.objects.filter(
        ticket_type=ticket_type,
        creator=creator,
        bk_biz_id=bk_biz_id,
        status__in=DEDUP_ACTIVE_STATUSES,
        create_at__gte=window_start,
    ).order_by("-id")

    for tk in candidates:
        try:
            if fingerprint_of(tk) == target_fingerprint:
                return tk
        except Exception:  # noqa - 历史单据 details 结构异常时跳过，不阻塞新提单
            continue

    return None
