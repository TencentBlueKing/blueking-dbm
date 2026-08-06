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
import ipaddress
import re

from django.http import HttpRequest

from backend.constants import IP_PORT_DIVIDER
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import (
    FakeRequest,
    auth_parse_clusters,
    auth_parse_hosts,
    auth_parse_instances,
)
from backend.dbm_aiagent.mcp_tools.typing import ClusterIdList

# 仅用于形态判断；合法性交给 ipaddress，避免 \d{1,3} 放过 999.x.x.x
_IPV4_SHAPE_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_IPV4_PORT_SHAPE_RE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$")


def _require_ip(value: str) -> str:
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise ValueError(f"invalid IP in target: {value}") from exc


def auth_parse_meta_value(request: HttpRequest, *args, **kwargs) -> ClusterIdList:
    """
    解析 get_meta_info 的 target 入参为集群 ID 列表。
    target 支持：
    - IP
    - IP:PORT
    - 集群域名
    """
    data = request.query_params if request.method == "GET" else request.data
    target = (data.get("target") or "").strip()
    if not target:
        raise ValueError("target is required")

    if _IPV4_SHAPE_RE.match(target):
        return auth_parse_hosts(FakeRequest(request.method, {"ip": _require_ip(target)}))

    matched = _IPV4_PORT_SHAPE_RE.match(target)
    if matched:
        ip = _require_ip(matched.group(1))
        port = int(matched.group(2))
        if not (1 <= port <= 65535):
            raise ValueError("target port must be an integer in 1..65535")
        return auth_parse_instances(FakeRequest(request.method, {"instance": f"{ip}{IP_PORT_DIVIDER}{port}"}))

    if "." in target:
        return auth_parse_clusters(FakeRequest(request.method, {"cluster_domain": target}))

    raise ValueError("target must be IP, IP:PORT, or cluster domain")
