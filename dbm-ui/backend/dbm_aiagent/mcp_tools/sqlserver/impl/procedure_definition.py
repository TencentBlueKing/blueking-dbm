# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQLServer 单存储过程定义体获取（按精确坐标 cluster_domain + dbname + 'schema.proc'）。

设计要点
- 单一 MCP 工具：`sqlserver_get_stored_procedure(cluster_domain, dbname, procedure)`，
  调用方必须已知确切 SP 名（不提供枚举/模糊匹配/批量），用于 LLM 静态风险/安全分析。
- 数据通道：必须 `USE [业务库]` 才能读到 sys.sql_modules，因此走
  `DRSApi.sqlserver_data_read_rpc`（业务库只读账号），与 `database_file_usage` 同通道，
  与 sync_status / instance_summary 走的 sys 通道不同。
- 三段标识符（dbname / schema / proc）必须经 `quote_sqlserver_ident` 严格白名单
  （`^[A-Za-z_][A-Za-z0-9_$#@]{0,127}$`），即使作为 N'...' 字面量传入也已过滤注入风险。
- 选实例：`resolve_target_instance` 缺省走 master，单 SP 查询不需要扇出到所有实例。
- 出参扁平：单次只查 1 个 SP，不嵌套 results 数组，所有字段拍平到顶层。

权限假设（依赖 `sqlserver_data_read_rpc` 通道账号的实际授权情况）
- 业务库 CONNECT：必备，否则 USE [dbname] 阶段失败；
- 业务库内 sys.sql_modules / sys.procedures / sys.objects / sys.schemas 只读：必备；
- 不需要 VIEW SERVER STATE，不需要 sysadmin。

不做的事（边界）
- 不做枚举：本工具不提供"列出 schema 下所有 SP"的能力；该能力由其他工具承担，
  本工具的存在前提是调用方已经知道 SP 全名。
- 不做模糊匹配：proc 名走严格等值过滤（N'name'），不做 LIKE，避免 LLM 拿模糊条件
  扫全库导致定义体洪流。
- 不做截断：超 max_definition_chars 直接 status=too_large + definition=null。
  截断会让风险分析失真（恰好少看一段就误判风险）。
- 不做脱敏：definition 是 sys.sql_modules.definition 原文，可能含硬编码凭据/密钥/IP，
  下游消费者是 LLM 风险扫描，必须看到原文；通过 `notice` 字段提示调用方不要原样回显。
- 不读系统 schema：sys / information_schema 显式拒绝，避免被用来探测系统对象。

字段语义（出参与 SQLServerProcedureDefinitionOutputSerializer 同源）
- status 是流程控制核心：
    * ok        -> definition 字段为 SP 原文
    * not_found -> 该 SP 不存在
    * encrypted -> SP 用了 WITH ENCRYPTION，sys.sql_modules.definition 为 NULL
    * too_large -> definition 字符数 > max_definition_chars，未返回 definition
    * error     -> RPC / USE / SELECT 阶段异常
- modify_date 取自 sys.objects.modify_date，作为"祖传代码"风险信号；
- definition_total_chars / line_count 用于估算 LLM 上下文消耗。
"""
from typing import Dict, Optional, Tuple

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.get_instance_address import resolve_target_instance
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.rpc_runner import run_user_db_read
from backend.dbm_aiagent.mcp_tools.sqlserver.helpers.sql_safety import quote_sqlserver_ident


class ProcedureDefinitionConstants:
    """获取 SP 定义体的常量集合。

    用途
        集中所有"行为相关常量"，与 serializers/procedure_definition.py 的 help_text
        必须保持同源，便于 LLM 拿到字段时同时读到判断规则。
    边界
        - 修改任一常量都需要同步修改 serializer help_text 与本文件模块 docstring，
          否则前后文档会漂移。
    """

    #: 默认 schema：当 procedure 入参不含点号时使用
    DEFAULT_SCHEMA: str = "dbo"
    #: 系统/限制 schema：禁止用本工具读取，避免被用来探测系统对象
    BLOCKED_SCHEMAS: Tuple[str, ...] = ("sys", "information_schema")
    #: 默认定义体字符上限（与 serializer InputSerializer.max_definition_chars.default 同源）
    DEFAULT_MAX_DEFINITION_CHARS: int = 200000
    #: 出参中固定的安全提醒（避免 LLM/调用方原样回显敏感原文给最终用户）
    NOTICE: str = (
        "definition is RAW T-SQL (not sanitized) for risk analysis; "
        "may contain hardcoded credentials/keys/IPs. Do NOT echo verbatim to end users."
    )
    #: 单一 RPC 操作名（用于 run_user_db_read 的错误信息标识）
    OP_NAME: str = "get_stored_procedure"


class ProcedureDefinitionSQL:
    """SP 定义体查询 SQL 容器。

    用途
        集中本工具用到的 SQL 模板，便于审计和后续兼容性维护。
    边界
        - 全部走 sys.* 系统视图（procedures / objects / schemas / sql_modules），
          列名在 SQL Server 2008+ 全版本稳定，无需运行期版本判定；
        - schema / proc 通过 N'...' 字面量传入，由 NameParser 阶段保证已过白名单；
        - is_ms_shipped = 0 排除微软出厂 SP，仅返回用户自建过程；
        - DATALENGTH 是字节，sys.sql_modules.definition 为 NVARCHAR(MAX)，故 /2 得字符数。
    """

    DEFINITION_TPL: str = """
SELECT TOP 1
    CONVERT(VARCHAR(19), o.modify_date, 120)                  AS modify_date,
    CASE WHEN sm.definition IS NULL THEN 1 ELSE 0 END         AS is_encrypted,
    CAST(ISNULL(DATALENGTH(sm.definition), 0) / 2 AS BIGINT)  AS definition_chars,
    sm.definition                                             AS definition
FROM sys.procedures p
JOIN sys.objects   o  ON o.object_id = p.object_id
JOIN sys.schemas   s  ON s.schema_id = o.schema_id
LEFT JOIN sys.sql_modules sm ON sm.object_id = p.object_id
WHERE o.is_ms_shipped = 0
  AND s.name = N'{schema}'
  AND o.name = N'{proc}'
""".strip()


class ProcedureNameParser:
    """SP 名称解析器：把 'schema.proc' / 'proc' 规整成 (schema, proc) 二元组。

    用途
        - 容忍 SSMS 风格的方括号包裹（如 [dbo].[usp_xxx]）；
        - 'proc' 单段时回填默认 schema=dbo；
        - 不做白名单校验，只做拆分，统一交给 quote_sqlserver_ident 校验。
    输入
        raw: 原始 procedure 入参字符串
    输出
        通过 `parse()` 返回 (schema, proc)
    边界
        - 三段及以上点号（如 db.schema.proc）拒绝：库名应通过 dbname 入参传入；
        - 空字符串 / 全空白拒绝；
        - 不消化任何 SQL 注释、不消化引号字符串，调用方应保证只传纯名称。
    """

    @staticmethod
    def parse(raw: str) -> Tuple[str, str]:
        """解析 SP 名称为 (schema, proc)。

        功能：拆分点号、去掉方括号包裹、回填默认 schema。
        输入：raw - 原始入参，例如 'dbo.usp_x' / 'usp_x' / '[dbo].[usp_x]'。
        输出：(schema, proc) 二元组，未指定 schema 时回退到
              ProcedureDefinitionConstants.DEFAULT_SCHEMA。
        边界：
            - raw 为空或全空白 -> DBMMcpBaseException;
            - 多于一个点号 -> DBMMcpBaseException（库名应走 dbname 入参）;
            - 拆分后任一段是空字符串 -> 由后续 quote_sqlserver_ident 拒绝。
        """
        if not raw or not raw.strip():
            raise DBMMcpBaseException(msg="procedure is empty")

        name = raw.strip()
        parts = []
        for piece in name.split("."):
            piece = piece.strip()
            if piece.startswith("[") and piece.endswith("]"):
                piece = piece[1:-1]
            parts.append(piece)

        if len(parts) == 1:
            return ProcedureDefinitionConstants.DEFAULT_SCHEMA, parts[0]
        if len(parts) == 2:
            schema = parts[0] or ProcedureDefinitionConstants.DEFAULT_SCHEMA
            return schema, parts[1]
        raise DBMMcpBaseException(msg=f"invalid procedure name '{raw}': expect 'schema.proc' or 'proc'")


class ProcedureDefinitionFetcher:
    """SP 定义体采集器：负责"USE 业务库 -> SELECT 元数据 + 定义体"的单实例 RPC。

    用途
        把 NameParser 解析后的 (schema, proc) 落到一次实际 RPC 调用，
        返回 sys.sql_modules 行（含定义体）。
    输入
        bk_cloud_id: 集群所在云区域
        target:      {"address": "ip:port", "role": "...", "is_stand_by": bool}
        quoted_db:   已经 quote_sqlserver_ident 包裹过的 [dbname]
    输出
        通过 `fetch()` 返回 dict（meta 行）或 None（SP 不存在）。
    边界
        - 只读，不修改任何对象；
        - schema / proc 在调用 fetch 前必须已经过 quote_sqlserver_ident 白名单；
        - 不做 status 判定（加密 / 超长 / 不存在），由上层 PayloadBuilder 处理；
        - RPC / USE / SELECT 阶段异常通过 DBMMcpBaseException 透传出去。
    """

    def __init__(self, bk_cloud_id: int, target: Dict, quoted_db: str):
        self._bk_cloud_id = bk_cloud_id
        self._target = target
        self._quoted_db = quoted_db

    def fetch(self, schema: str, proc: str) -> Optional[Dict]:
        """采集单个 SP 的元数据 + 定义体。

        功能：拼 SQL、走 run_user_db_read、取 TOP 1 行。
        输入：schema / proc - 已通过 quote_sqlserver_ident 白名单的标识符段。
        输出：
            - 命中 -> {"modify_date","is_encrypted","definition_chars","definition"}
            - 未命中 -> None
        边界：
            - run_user_db_read 抛 DBMMcpBaseException 时直接向上抛，
              由 sqlserver_get_stored_procedure 转 status=error。
        """
        sql = ProcedureDefinitionSQL.DEFINITION_TPL.format(schema=schema, proc=proc)
        rows = run_user_db_read(
            self._bk_cloud_id,
            self._target["address"],
            self._quoted_db,
            sql,
            ProcedureDefinitionConstants.OP_NAME,
        )
        if not rows:
            return None
        return rows[0]


class ProcedureDefinitionPayloadBuilder:
    """出参组装器：把 Fetcher 的原始行转成 5 种 status 之一的扁平 payload。

    用途
        统一出参 schema、统一 status 分支判定逻辑，便于 serializer 校验。
    输入
        cluster_domain / target / dbname / procedure / max_definition_chars
    输出
        通过 `build_*()` 系列方法返回与
        SQLServerProcedureDefinitionOutputSerializer 同构的 dict。
    边界
        - 不做任何 RPC 调用，是纯组装器；
        - is_encrypted / status 判定基于 sys.sql_modules.definition 是否为 NULL；
        - too_large 判定基于 definition_chars > max_definition_chars，
          为防止 LLM 拿到截断的定义体做错误风险判断，**不做截断**。
    """

    def __init__(
        self,
        cluster_domain: str,
        target: Dict,
        dbname: str,
        procedure: str,
        max_definition_chars: int,
    ):
        self._base = {
            "cluster_domain": cluster_domain,
            "address": target["address"],
            "role": target["role"],
            "dbname": dbname,
            "procedure": procedure,
            "status": "ok",
            "error": None,
            "modify_date": None,
            "is_encrypted": 0,
            "definition_total_chars": 0,
            "line_count": 0,
            "definition": None,
            "notice": ProcedureDefinitionConstants.NOTICE,
        }
        self._max_chars = max_definition_chars

    # ---------- public ----------
    def build_error(self, err_msg: str) -> Dict:
        """status=error：RPC / USE / SELECT 阶段异常。

        功能：包装 DBMMcpBaseException 的 msg 为 status=error 的标准出参。
        输入：err_msg - 异常字符串
        输出：扁平 payload
        边界：定义体相关字段保持默认值（None / 0）。
        """
        return {**self._base, "status": "error", "error": err_msg}

    def build_not_found(self, schema: str, proc: str) -> Dict:
        """status=not_found：SP 不存在。

        功能：返回 SP 未命中的标准出参。
        输入：schema / proc - 已解析的两段名
        输出：扁平 payload，error 字段说明完整坐标。
        边界：定义体相关字段保持默认值。
        """
        return {
            **self._base,
            "status": "not_found",
            "error": f"procedure '{schema}.{proc}' not found in database '{self._base['dbname']}'",
        }

    def build_from_meta(self, meta: Dict, schema: str, proc: str) -> Dict:
        """根据 Fetcher 行构建 ok / encrypted / too_large 三种 status。

        功能：基于 sys.sql_modules 行做 3 路分支：
              * is_encrypted=1   -> status=encrypted
              * 超 max_chars     -> status=too_large
              * 其余             -> status=ok
        输入：
            meta:   Fetcher.fetch 返回的单行 dict
            schema/proc: 用于错误信息中标注完整坐标
        输出：扁平 payload
        边界：
            - 加密 SP 的 definition 一定为 NULL，definition_total_chars 也为 0；
            - too_large 时 definition 字段不返回（None），保持 status 与 size 信号；
            - line_count 仅在 status=ok 时计算，避免对未返回内容做误算。
        """
        is_encrypted = int(meta.get("is_encrypted") or 0)
        def_chars = int(meta.get("definition_chars") or 0)

        payload = {
            **self._base,
            "modify_date": meta.get("modify_date"),
            "is_encrypted": is_encrypted,
            "definition_total_chars": def_chars,
        }

        if is_encrypted == 1:
            payload["status"] = "encrypted"
            payload["error"] = (
                f"procedure '{schema}.{proc}' is encrypted with WITH ENCRYPTION; " "definition is not retrievable"
            )
            return payload

        if def_chars > self._max_chars:
            payload["status"] = "too_large"
            payload["error"] = (
                f"definition size {def_chars} chars exceeds "
                f"max_definition_chars={self._max_chars}; "
                "increase max_definition_chars or fetch via SSMS for offline review"
            )
            return payload

        body = meta.get("definition") or ""
        payload["status"] = "ok"
        payload["error"] = None
        payload["definition"] = body
        payload["line_count"] = (body.count("\n") + 1) if body else 0
        return payload


def sqlserver_get_stored_procedure(
    cluster_domain: str,
    dbname: str,
    procedure: str,
    max_definition_chars: int = ProcedureDefinitionConstants.DEFAULT_MAX_DEFINITION_CHARS,
    address: Optional[str] = None,
) -> Dict:
    """按精确坐标获取 SQLServer 单个 SP 的完整原始定义体（MCP 工具入口）。

    功能
        编排：名称解析 -> 三段标识符白名单 -> 屏蔽系统 schema -> 选实例
        -> RPC 采集 -> 出参组装。
    输入
        cluster_domain:        集群不可变域名 (immute_domain)
        dbname:                业务库名（承载该 SP 的数据库）
        procedure:             'schema.proc' 或 'proc'（缺省 schema=dbo）
        max_definition_chars:  定义体字符上限，超出 -> status=too_large（不截断）
        address:               可选实例地址；不传缺省走 master
    输出
        与 SQLServerProcedureDefinitionOutputSerializer 同构的扁平 dict，
        status ∈ {ok, not_found, encrypted, too_large, error}。
    边界
        - 名称非法 / 系统 schema 拒绝 -> 直接抛 DBMMcpBaseException（由 mcp 装饰器
          统一兜底，与本文件其他工具的快速失败行为一致）；
        - RPC / USE / SELECT 阶段异常 -> status=error，不抛出，便于 LLM 决策；
        - 单实例工具：不扇出到 secondary，因为 SP 定义在主从一致，无须重复采集。
    """
    # 1) 解析 'schema.proc'
    eff_schema, proc = ProcedureNameParser.parse(procedure)

    # 2) 三段标识符严格白名单
    quoted_db = quote_sqlserver_ident(dbname)
    quote_sqlserver_ident(eff_schema)
    quote_sqlserver_ident(proc)

    # 3) 屏蔽系统 schema
    if eff_schema.lower() in ProcedureDefinitionConstants.BLOCKED_SCHEMAS:
        raise DBMMcpBaseException(msg=f"schema '{eff_schema}' is not allowed for stored procedure query")

    # 4) 选实例（缺省 master）
    bk_cloud_id, target = resolve_target_instance(cluster_domain, address)

    # 5) 组装出参 builder + RPC fetcher
    builder = ProcedureDefinitionPayloadBuilder(
        cluster_domain=cluster_domain,
        target=target,
        dbname=dbname,
        procedure=procedure,
        max_definition_chars=max_definition_chars,
    )
    fetcher = ProcedureDefinitionFetcher(bk_cloud_id, target, quoted_db)

    # 6) RPC 采集
    try:
        meta = fetcher.fetch(eff_schema, proc)
    except DBMMcpBaseException as exc:
        return builder.build_error(str(exc))

    # 7) 分支组装
    if meta is None:
        return builder.build_not_found(eff_schema, proc)
    return builder.build_from_meta(meta, eff_schema, proc)
