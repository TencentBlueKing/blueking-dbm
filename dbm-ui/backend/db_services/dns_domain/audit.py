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

from backend.constants import DEFAULT_SYSTEM_USER
from backend.db_services.dns_domain.format import normalize_domain
from backend.db_services.dns_domain.models import DnsDomainAuditLog
from backend.utils.local import local

logger = logging.getLogger("root")


def client_ip_from_request(request) -> str:
    if request is None:
        return ""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def current_actor():
    operator = DEFAULT_SYSTEM_USER
    client_ip = ""
    try:
        request = local.request
    except Exception:  # pylint: disable=broad-except
        request = None
    if request is None:
        return operator, client_ip
    user = getattr(request, "user", None)
    username = getattr(user, "username", "") if user else ""
    if username:
        operator = username
    return operator, client_ip_from_request(request)


def record_mapping_change(domain: str, action: str, lines: list, operator: str = "", client_ip: str = ""):
    """记录一条已生效的域名变更。写日志失败不影响域名操作本身。"""
    content = [line for line in lines if line]
    if not content:
        return None
    if not operator:
        operator, actor_ip = current_actor()
        client_ip = client_ip or actor_ip
    try:
        return DnsDomainAuditLog.objects.create(
            domain=normalize_domain(domain),
            operator=operator,
            client_ip=client_ip or "",
            action=action,
            change_lines=content,
        )
    except Exception:  # pylint: disable=broad-except
        logger.exception("record dns domain audit failed, domain=%s action=%s", domain, action)
        return None
