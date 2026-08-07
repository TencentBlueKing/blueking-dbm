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
from backend.dbm_aiagent.mcp_tools.common.impl.bkcc_wrap.check_operator import check_operator
from backend.dbm_aiagent.mcp_tools.common.impl.bkcc_wrap.list_hosts_without_biz import list_hosts_without_biz
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpForbiddenException

# 单次批量校验/下发的最大 IP 数，超出需分批（避免 CMDB in 查询超限或性能劣化）
MAX_IPS = 100


def check_machines_operator(bk_cloud_id: int, ips: list[str], username: str) -> list[dict]:
    """
    校验目标机器存在且由执行人负责，返回命中 CMDB 的主机列表。

    校验内容：
    1. IP 去重，并限制批量数量（超过 MAX_IPS 直接报错提示分批）；
    2. IP 必须在 CMDB 中存在，否则提示缺失的机器；
    3. 执行人必须是机器的负责人（operator）或备份负责人（bk_bak_operator），否则明确提示。
    """
    ips = sorted(set(ips))
    if len(ips) > MAX_IPS:
        raise DBMMcpForbiddenException(
            msg=f"ips count {len(ips)} exceeds the limit {MAX_IPS}, please split into batches"
        )
    hosts = list_hosts_without_biz(bk_cloud_id=bk_cloud_id, ips=ips)
    found_ips = {host.get("bk_host_innerip") for host in hosts}
    missing_ips = set(ips) - found_ips
    if missing_ips:
        raise DBMMcpForbiddenException(msg=f"machines {sorted(missing_ips)} not found in CMDB")
    # 校验执行者身份：非机器负责人或备份负责人时明确提示用户
    try:
        check_operator(username=username, bk_host_ids=[host["bk_host_id"] for host in hosts])
    except DBMMcpForbiddenException as err:
        raise DBMMcpForbiddenException(msg=f"用户 {username} 不是目标机器的负责人或备份负责人，无权限执行") from err
    return hosts
