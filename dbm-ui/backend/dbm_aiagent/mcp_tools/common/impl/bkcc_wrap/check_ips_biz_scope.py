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
from backend.components import CCApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpForbiddenException


def check_ips_biz_scope(bk_scope_type: str, bk_scope_id: str, hosts: list[dict]):
    """校验目标 IP 归属业务与传入 bk_scope_id（业务ID）一致。

    仅当 bk_scope_type == "biz" 时做严格校验（业务集等复杂范围暂不校验）：
    通过 CMDB 查询主机业务归属，逐主机校验「每台机器都必须归属传入业务ID」，
    任一主机不归属即抛 DBMMcpForbiddenException 并提示实际归属业务，
    避免调用方猜测业务ID或跨业务批量越权操作。

    :param bk_scope_type: 资源范围类型（biz / biz_set）
    :param bk_scope_id: 资源范围 ID，bk_scope_type=biz 时必须为用户提供的业务ID
    :param hosts: 已通过 CMDB 存在性校验的主机列表（含 bk_host_id）
    """
    if bk_scope_type != "biz":
        return
    try:
        expected_biz_id = int(bk_scope_id)
    except (TypeError, ValueError):
        raise DBMMcpForbiddenException(
            msg=f"bk_scope_type 为 biz 时 bk_scope_id 必须是业务ID（数字），当前为 {bk_scope_id}，请提供正确的业务ID"
        )
    host_ids = [host["bk_host_id"] for host in hosts]
    if not host_ids:
        raise DBMMcpForbiddenException(msg="无有效主机可校验业务归属")
    rel_info = CCApi.find_host_biz_relations({"bk_host_id": host_ids}, use_admin=True) or []
    # 构建 host_id -> 该主机归属业务集合 的映射（同一主机可能归属多个业务）
    host_biz_map: dict[int, set[int]] = {}
    for rel in rel_info:
        if rel.get("bk_host_id") is None or rel.get("bk_biz_id") is None:
            continue
        host_biz_map.setdefault(int(rel["bk_host_id"]), set()).add(int(rel["bk_biz_id"]))
    # 逐主机校验：每台机器都必须归属 expected_biz_id，而非「命中并集」
    mismatched = {}
    for host in hosts:
        host_id = int(host["bk_host_id"])
        actual_biz_ids = host_biz_map.get(host_id, set())
        if expected_biz_id not in actual_biz_ids:
            mismatched[host.get("bk_host_innerip") or host_id] = actual_biz_ids
    if mismatched:
        detail = "; ".join(f"{ip}:{sorted(actual) or '无归属'}" for ip, actual in mismatched.items())
        raise DBMMcpForbiddenException(msg=f"以下主机不属于业务 {expected_biz_id}（{detail}）。业务ID必须由用户提供，请使用正确的业务ID后重试")
