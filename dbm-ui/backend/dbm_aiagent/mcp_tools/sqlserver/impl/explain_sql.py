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
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import (
    quote_sqlserver_ident,
    sanitize_select_sql_for_sqlserver,
)


def _extract_explain_xml(table_data) -> str:
    """从 SHOWPLAN_XML 的返回结果中提取 XML 文本。

    SQL Server SHOWPLAN_XML 模式下，结果列名通常为
    "Microsoft SQL Server 2005 XML Showplan"，但不同版本/驱动可能略有差异。
    这里：
      1. 优先按列名（含 "Showplan"）匹配
      2. 兜底取首列 value
      3. 用 "<ShowPlanXML" 前缀做格式校验，过滤掉非 XML 行
      4. 多行（多 statement 场景）按出现顺序拼接
    """
    xml_parts = []
    for row in table_data:
        if not isinstance(row, dict) or not row:
            continue
        val = None
        # 优先按已知列名（不区分大小写）查找
        for k, v in row.items():
            if isinstance(k, str) and "showplan" in k.lower():
                val = v
                break
        # 兜底：取第一个 value
        if val is None:
            val = next(iter(row.values()))
        if isinstance(val, str) and val.lstrip().startswith("<ShowPlanXML"):
            xml_parts.append(val)
    if not xml_parts:
        raise DBMMcpBaseException(msg="explain sql returned no valid ShowPlanXML")
    return "\n".join(xml_parts)


def sqlserver_explain_sql(
    cluster_domain: str,
    dbname: str,
    query_sql: str,
    address: Optional[str] = None,
) -> Dict:
    """获取用户 SQL 的估算执行计划（XML 格式）。

    安全模型（纵深防御）：
      1. 应用层 sanitize_select_sql_for_sqlserver：
         - 白名单：仅允许 SELECT / WITH(CTE) 开头
         - 黑名单：拦截写操作、DDL、xp_/sp_、WAITFOR、USE/GO、OPENROWSET、BULK 等
         - 多语句拦截、字符串字面量剥离后做关键字匹配（避免误杀）
         - SQL 长度上限（防编译期 DoS）
      2. dbname 经 quote_sqlserver_ident 严格校验后用 [] 包裹
      3. 远端启用 SET SHOWPLAN_XML ON：SQL Server 只编译不执行，
         返回 XML 计划，不会真正读取/写入数据
      4. 末尾追加 SET SHOWPLAN_XML OFF，防止 RPC 连接复用时污染下一个请求

    使用通道：sqlserver_data_read_rpc
      - sqlserver_sys_read_rpc 没有业务库 SHOWPLAN/SELECT 权限
      - sqlserver_data_read_rpc 拥有业务库只读账号权限，可走估算计划

    cmds 顺序（同连接顺序执行，每条独立 batch）：
      1) USE [dbname]
      2) SET SHOWPLAN_XML ON
      3) <用户 SQL>             ← 此条只返回 XML 计划，不执行
      4) SET SHOWPLAN_XML OFF   ← 关闭开关，防连接池复用污染

    :param cluster_domain: 集群不可变域名
    :param dbname: 目标数据库名（仅允许 [A-Za-z_][A-Za-z0-9_$#@]{0,127}）
    :param query_sql: 用户提交的 SELECT/WITH 语句
    :param address: 可选，指定具体实例；不传则缺省走 master
    :return: {
        "cluster_domain": "...",
        "address": "ip:port",
        "role": "...",
        "dbname": "...",
        "explain_xml": "<ShowPlanXML ...>...</ShowPlanXML>",
        "rewritten": False,
        "is_trivial": False,   # 是否为无真实查询计划的平凡语句（如 SELECT 1）
    }
    """
    # 1. 入参安全校验
    quoted_db = quote_sqlserver_ident(dbname)
    clean_sql, was_rewritten = sanitize_select_sql_for_sqlserver(query_sql)

    # 2. 解析目标实例
    bk_cloud_id, instances = resolve_sqlserver_addresses(
        cluster_domain=cluster_domain, address=address, default_role="master"
    )
    target = instances[0]

    # 3. 构造 cmds：USE → SHOWPLAN_XML ON → 用户 SQL → SHOWPLAN_XML OFF
    cmds = [
        f"USE {quoted_db};",
        "SET SHOWPLAN_XML ON;",
        clean_sql,
        "SET SHOWPLAN_XML OFF;",
    ]

    rpc_results = DRSApi.sqlserver_data_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [target["address"]],
            "cmds": cmds,
        }
    )

    rpc_res = rpc_results[0]
    if rpc_res.get("error_msg"):
        raise DBMMcpBaseException(msg=rpc_res["error_msg"])

    cmd_results = rpc_res.get("cmd_results") or []
    # 至少要有前 3 条结果；第 4 条 SHOWPLAN OFF 失败仅 warning，不阻断主流程
    if len(cmd_results) < 3:
        raise DBMMcpBaseException(msg="unexpected rpc result: missing cmd_results")

    # USE 失败：库名不存在或账号无访问权限
    if cmd_results[0].get("error_msg"):
        raise DBMMcpBaseException(msg=f"change db to {dbname} failed: {cmd_results[0]['error_msg']}")

    # SET SHOWPLAN_XML ON 失败：极少数情况（语法不支持），权限错误一般不在这里报
    if cmd_results[1].get("error_msg"):
        raise DBMMcpBaseException(msg=f"enable showplan_xml failed: {cmd_results[1]['error_msg']}")

    # 用户 SQL 编译失败（含 SHOWPLAN 权限缺失，权限校验通常在这一步触发）
    explain_res = cmd_results[2]
    if explain_res.get("error_msg"):
        err = explain_res["error_msg"]
        if "SHOWPLAN permission denied" in err:
            raise DBMMcpBaseException(
                msg=(
                    f"该账号在数据库 '{dbname}' 中缺少 SHOWPLAN 权限，无法获取执行计划。"
                    f"请联系 DBA 执行：USE [{dbname}]; GRANT SHOWPLAN TO <只读账号>;"
                    f" 原始报错：{err}"
                )
            )
        raise DBMMcpBaseException(msg=f"explain sql failed: {err}")

    table_data = explain_res.get("table_data") or []
    if not table_data:
        raise DBMMcpBaseException(msg="explain sql returned empty result")

    explain_xml = _extract_explain_xml(table_data)

    # 简单识别：是否为 SELECT WITHOUT QUERY（无真正查询计划，如 SELECT 1）
    # 上层 Agent 可据此跳过深度分析
    is_trivial = ("SELECT WITHOUT QUERY" in explain_xml) and ("<QueryPlan" not in explain_xml)

    return {
        "cluster_domain": cluster_domain,
        "address": target["address"],
        "role": target["role"],
        "dbname": dbname,
        "explain_xml": explain_xml,
        "rewritten": was_rewritten,
        "is_trivial": is_trivial,
    }
