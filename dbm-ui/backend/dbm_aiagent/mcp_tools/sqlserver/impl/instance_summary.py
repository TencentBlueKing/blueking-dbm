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

# 实例基础信息查询 SQL：从 SERVERPROPERTY、sys.dm_os_sys_info、sys.dm_os_process_memory、
# sys.configurations 四个数据源拼接为单条 SELECT。
#
# 版本兼容（覆盖 SQL Server 2008 ~ 2019）：
#   - SERVERPROPERTY('IsHadrEnabled')：2012 引入；2008/2008R2 上调用返回 NULL，不报错
#   - sys.dm_os_sys_info.cpu_count：2008+ 都有
#   - sys.dm_os_process_memory.physical_memory_in_use_kb：2008+ 都有，列名各版本一致
#   - sys.configurations.'max/min server memory (MB)'：2005+ 都有
#   - 实例启动时间不取 dm_os_sys_info.sqlserver_start_time（2008 没有），
#     改用 4 个系统会话最早的 login_time 近似，全版本可用
#
# 设计原则：
#   - 整批就一条 SELECT，不使用 DECLARE / SET / EXEC / sp_executesql / SET NOCOUNT，
#     避免被 DRS 的"非只读语句"检测拦截，也避免多结果集挤掉真正的数据行
#   - 所有引用的视图列名都在 2008+ 上稳定存在，无需运行期版本判定
_INSTANCE_SUMMARY_SQL = """
SELECT
    CAST(SERVERPROPERTY('MachineName')              AS NVARCHAR(256)) AS machine_name,
    CAST(SERVERPROPERTY('ServerName')               AS NVARCHAR(256)) AS server_name,
    CAST(SERVERPROPERTY('InstanceName')             AS NVARCHAR(256)) AS instance_name,
    CAST(SERVERPROPERTY('ProductVersion')           AS NVARCHAR(64))  AS product_version,
    CAST(SERVERPROPERTY('ProductLevel')             AS NVARCHAR(64))  AS product_level,
    CAST(SERVERPROPERTY('Edition')                  AS NVARCHAR(128)) AS edition,
    CAST(SERVERPROPERTY('Collation')                AS NVARCHAR(128)) AS collation,
    CAST(SERVERPROPERTY('IsClustered')              AS INT)           AS is_clustered,
    CAST(SERVERPROPERTY('IsHadrEnabled')            AS INT)           AS is_hadr_enabled,
    CAST(SERVERPROPERTY('IsIntegratedSecurityOnly') AS INT)           AS is_integrated_security_only,
    (SELECT cpu_count FROM sys.dm_os_sys_info)                        AS cpu_count,
    (SELECT MIN(login_time) FROM sys.dm_exec_sessions WHERE session_id <= 4) AS sqlserver_start_time,
    -- 内存信息：以 MB 为单位，全部走 2008+ 都存在的视图与配置项，无版本判断
    -- sys.dm_os_process_memory：2008 起，physical_memory_in_use_kb 列名各版本一致
    (SELECT physical_memory_in_use_kb / 1024 FROM sys.dm_os_process_memory) AS sql_memory_used_mb,
    -- sys.configurations：2005 起，'max/min server memory (MB)' 名称各版本一致，value_in_use 是当前生效值
    (SELECT CAST(value_in_use AS BIGINT) FROM sys.configurations WHERE name = 'max server memory (MB)') AS sql_memory_max_mb,
    (SELECT CAST(value_in_use AS BIGINT) FROM sys.configurations WHERE name = 'min server memory (MB)') AS sql_memory_min_mb
""".strip()


def sqlserver_instance_summary(cluster_domain: str, address: Optional[str] = None) -> Dict:
    """查询 sqlserver 实例的基础信息。

    使用通道：sqlserver_sys_read_rpc（仅访问系统视图，无需业务库权限）。

    :param cluster_domain: 集群不可变域名
    :param address: 可选，指定具体实例 "ip:port"；不传则返回集群内全部实例
    :return: {
        "cluster_domain": "...",
        "results": [
            {
                "address": "ip:port",
                "role": "<inner_role>",
                "is_stand_by": bool,
                "data": { ...一行 SERVERPROPERTY 结果... },
                "error_msg": ""        # 单实例失败时填充，不影响其他实例
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
            "cmds": [_INSTANCE_SUMMARY_SQL],
        }
    )

    # 把 rpc 返回按 address 索引，便于和 instances 元信息合并
    address_to_rpc = {res["address"]: res for res in rpc_results}

    results = []
    for item in instances:
        rpc_res = address_to_rpc.get(item["address"])
        if rpc_res is None:
            results.append({**item, "data": None, "error_msg": "no rpc response"})
            continue

        if rpc_res.get("error_msg"):
            results.append({**item, "data": None, "error_msg": rpc_res["error_msg"]})
            continue

        cmd_res = rpc_res["cmd_results"][0]
        if cmd_res.get("error_msg"):
            results.append({**item, "data": None, "error_msg": cmd_res["error_msg"]})
            continue

        table_data = cmd_res.get("table_data") or []
        results.append(
            {
                **item,
                "data": table_data[0] if table_data else None,
                "error_msg": "",
            }
        )

    if not results:
        raise DBMMcpBaseException(msg="no instance result returned")

    return {"cluster_domain": cluster_domain, "results": results}
