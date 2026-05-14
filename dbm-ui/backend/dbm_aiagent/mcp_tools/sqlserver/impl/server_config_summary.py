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
from typing import Dict, Optional

from backend.components import DRSApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_sqlserver_addresses

# 关注的关键配置白名单：覆盖性能/安全两个维度，按需扩展
# 使用固定 IN 列表，避免任意配置项查询导致输出膨胀
_CONFIG_WHITELIST = (
    "max server memory (MB)",
    "min server memory (MB)",
    "max degree of parallelism",
    "cost threshold for parallelism",
    "optimize for ad hoc workloads",
    "max worker threads",
    "remote query timeout (s)",
    "Agent XPs",
    "xp_cmdshell",
    "clr enabled",
    "remote access",
    "remote admin connections",
    "default trace enabled",
)


def _build_config_summary_sql() -> str:
    """根据白名单构建配置查询 SQL，使用参数化字面量列表。

    白名单元素均为内置常量，不接受外部输入，因此可安全拼接。
    """
    name_list = ",".join(f"N'{name}'" for name in _CONFIG_WHITELIST)
    return f"""
SELECT
    name,
    value,
    value_in_use,
    minimum,
    maximum,
    is_dynamic,
    is_advanced,
    description
FROM master.sys.configurations
WHERE name IN ({name_list})
ORDER BY name
""".strip()


_SERVER_CONFIG_SQL = _build_config_summary_sql()


def sqlserver_server_config_summary(cluster_domain: str, address: Optional[str] = None) -> Dict:
    """查询 sqlserver 实例的关键服务器配置（基于白名单）。

    使用通道：sqlserver_sys_read_rpc。

    :param cluster_domain: 集群不可变域名
    :param address: 可选，指定具体实例；不传则查询集群内全部实例
    :return: {
        "cluster_domain": "...",
        "results": [
            {
                "address": "ip:port",
                "role": "...",
                "is_stand_by": bool,
                "configurations": [ ...每行一个配置项... ],
                "error_msg": ""
            }, ...
        ]
    }
    """
    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="all"
    )

    rpc_results = DRSApi.sqlserver_sys_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [item["address"] for item in instances],
            "cmds": [_SERVER_CONFIG_SQL],
        }
    )
    address_to_rpc = {res["address"]: res for res in rpc_results}

    results = []
    for item in instances:
        rpc_res = address_to_rpc.get(item["address"])
        if rpc_res is None:
            results.append({**item, "configurations": [], "error_msg": "no rpc response"})
            continue

        if rpc_res.get("error_msg"):
            results.append({**item, "configurations": [], "error_msg": rpc_res["error_msg"]})
            continue

        cmd_res = rpc_res["cmd_results"][0]
        if cmd_res.get("error_msg"):
            results.append({**item, "configurations": [], "error_msg": cmd_res["error_msg"]})
            continue

        results.append(
            {
                **item,
                "configurations": cmd_res.get("table_data") or [],
                "error_msg": "",
            }
        )

    if not results:
        raise DBMMcpBaseException(msg="no instance result returned")

    return {"cluster_domain": cluster_domain, "results": results}
