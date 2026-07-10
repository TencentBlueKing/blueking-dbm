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
from urllib.parse import urlparse

from django.utils.translation import gettext as _


def extract_ip_from_addr(addr: str) -> str:
    """从 DTS OpenAPI addr 中提取 IP。

    实测 OpenAPI 返回格式不对称，不能按端口含义解析，只能抽 host：

    - Master：``http://127.0.0.1:18401``（peer-urls，带 scheme；端口是 peer 不是 master-addr）
    - Worker：``127.0.0.1:18501``（worker-addr，无 scheme）

    不能简单 ``rsplit(':', 1)``，否则 Master 会得到 ``http://127.0.0.1``。
    """
    if not addr:
        return ""
    raw = addr.strip()
    if "://" not in raw:
        # 无 scheme：host:port / [ipv6]:port / bare host
        raw = f"//{raw}"
    parsed = urlparse(raw)
    host = parsed.hostname or ""
    return host.strip("[]")


def format_api_nodes(api_items: list) -> str:
    """格式化 OpenAPI 节点列表，便于验收失败日志对照。

    MasterItem 有 alive/leader；WorkerItem 有 bound_stage，无 alive。
    """
    parts = []
    for item in api_items or []:
        name = getattr(item, "name", "") or ""
        addr = getattr(item, "addr", "") or ""
        extras = []
        if hasattr(item, "alive"):
            extras.append(f"alive={getattr(item, 'alive')}")
        if hasattr(item, "leader"):
            extras.append(f"leader={getattr(item, 'leader')}")
        if hasattr(item, "bound_stage"):
            extras.append(f"bound_stage={getattr(item, 'bound_stage') or ''}")
        suffix = f"({', '.join(extras)})" if extras else ""
        parts.append(f"{name}@{addr}{suffix}")
    return ", ".join(parts) if parts else _("(空)")


def format_expected_nodes(expected_nodes: list[dict]) -> str:
    parts = []
    for node in expected_nodes or []:
        ip = node.get("ip") or ""
        name = node.get("name") or ""
        port = node.get("port")
        if name and port is not None:
            parts.append(f"{name}@{ip}:{port}")
        elif name:
            parts.append(f"{name}@{ip}")
        else:
            parts.append(str(ip))
    return ", ".join(parts) if parts else _("(空)")


def match_nodes(api_items: list, expected_nodes: list[dict], role: str) -> None:
    """校验期望节点均已出现在 OpenAPI 列表中；不匹配时抛出带明细的 ValueError。

    只按 IP 匹配：Master OpenAPI addr 端口是 peer(18401)，与部署期望的 master-addr(18301)
    不一致，不能拿 addr 端口与 expected.port 比对。
    """
    if not expected_nodes:
        return

    api_ips = {extract_ip_from_addr(getattr(item, "addr", "") or "") for item in api_items}
    api_ips.discard("")
    expected_ips = [node.get("ip") for node in expected_nodes if node.get("ip")]
    missing = [ip for ip in expected_ips if ip not in api_ips]
    if not missing:
        return

    raise ValueError(
        _("{} 节点未全部注册: 缺失={}, 期望={}, 实际注册={}, 解析到的 IP={}").format(
            role,
            missing,
            format_expected_nodes(expected_nodes),
            format_api_nodes(api_items),
            sorted(api_ips),
        )
    )
