# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQL 文本脱敏工具。

适用场景：从 sys.dm_exec_sql_text 取回的 SQL 文本可能含有敏感信息（手机号、密码、
身份证、邮箱，以及存储过程调用的参数实参等）。在返回给上层（含 AI 分析）之前，
应先经过本模块脱敏。

策略：
1. 若 SQL 以 EXEC / EXECUTE 开头，视为存储过程调用，所有实参一律打掉（方案 A）：
   - sp_executesql：保留前 2 个参数（SQL 模板 + 参数声明），之后所有实参替换。
   - 命名参数 @xxx=值          → @xxx=<REDACTED>
   - 位置参数 EXEC sp v1, v2  → EXEC sp <REDACTED>, <REDACTED>
2. 普通 SQL：仅对高危模式做脱敏（手机号、身份证、邮箱、password=/pwd=/token= 等），
   保留 SQL 字面量结构，避免破坏 AI 对语义的理解。

"""

import logging
import re
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger("root")

#: 脱敏占位符，便于上层识别本字段已被处理
REDACTED = "<REDACTED>"
#: 脱敏过程异常时的占位符——绝不返回原文，避免敏感信息因异常路径泄露
SANITIZE_FAILED = "<SANITIZE_FAILED>"

# ------------------------------------------------------------
# 通用敏感模式（用于普通 SQL 分支）
# 仅命中"明确就是敏感数据"的模式，避免误伤 SQL 字面量
# ------------------------------------------------------------

# 中国手机号：以 1 开头的 11 位数字（前后需为非数字边界，避免误命中长串数字）
_RE_PHONE_CN = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
# 18 位身份证（含 X 校验位）
_RE_IDCARD_CN = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")
# 邮箱
_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# password=xxx / pwd='xxx' / token = "xxx" / api_key=xxx —— 等号右侧值整体替换
# 同时覆盖：无引号、单引号、双引号、N'...' 形式
_RE_SECRET_KV = re.compile(
    r"""(?ix)
        \b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key)
        \s*=\s*
        (?: N?'(?:[^']|'')*'   # 单引号字符串（可带 N 前缀，支持 '' 转义）
          |   "(?:[^"]|"")*"   # 双引号字符串
          |   [^\s,;)]+        # 无引号裸值，到分隔符为止
        )
    """,
)

# ------------------------------------------------------------
# SP 调用相关模式
# ------------------------------------------------------------

# 是否为 EXEC / EXECUTE 开头（允许前导空白、注释暂不考虑）
_RE_EXEC_PREFIX = re.compile(r"^\s*(?:exec|execute)\b", re.IGNORECASE)

# 是否为 sp_executesql 调用
_RE_SP_EXECUTESQL = re.compile(r"^\s*(?:exec|execute)\s+sp_executesql\b", re.IGNORECASE)

# 命名参数赋值：@name = '值' / @name = N'值' / @name = 数字 / @name = 标识符
# 等号右侧整体被替换；为避免破坏后续解析，采用"按字符串/数字/标识"逐类匹配
_RE_NAMED_PARAM_VALUE = re.compile(
    r"""(?x)
        (@\w+\s*=\s*)              # 捕获组1：参数名 + 等号
        (?:
            N?'(?:[^']|'')*'       # 单引号字符串（可带 N 前缀）
          |   "(?:[^"]|"")*"       # 双引号字符串（标识符引用，少见）
          |   0x[0-9A-Fa-f]+       # 16 进制
          |   -?\d+(?:\.\d+)?      # 数字
          |   \w+                  # 裸标识符（如 NULL、DEFAULT、变量）
        )
    """,
)


def _redact_named_params(text: str) -> str:
    """把所有 @xxx=值 替换为 @xxx=<REDACTED>。"""
    return _RE_NAMED_PARAM_VALUE.sub(lambda m: f"{m.group(1)}{REDACTED}", text)


def _redact_sp_executesql(text: str) -> str:
    """sp_executesql 特殊处理：保留前 2 个参数，命名参数实参全打掉。

    sp_executesql 的形态：
        EXEC sp_executesql N'SQL模板', N'@p1 int,@p2 nvarchar(20)', @p1=1, @p2=N'xxx'
    其中前 2 个参数（SQL 模板 + 参数声明）本身不含敏感数据，保留以便分析；
    后面 @p1=1, @p2=N'xxx' 是真正的实参，必须打掉。
    """
    # 直接复用命名参数替换：前 2 个参数没有 @xxx= 形式，不会被误伤
    return _redact_named_params(text)


def _redact_positional_params(text: str) -> str:
    """位置参数 SP 调用：EXEC procName v1, v2, ... → EXEC procName <REDACTED>, <REDACTED>, ...

    匹配 EXEC / EXECUTE 后的过程名（含 [db].[schema].[name] 形态），
    将其后到行尾（或语句尾分号前）的所有实参整体替换。
    """
    # EXEC [db].[schema].[name]   或   EXEC name
    proc_pattern = re.compile(
        r"""(?ix)
            ^(\s*(?:exec|execute)\s+
              (?:\[?\w+\]?\.){0,2}\[?\w+\]?     # 过程名
            )
            \s+
            (.+?)                                # 参数列表
            (\s*;?\s*)$                          # 可能的分号尾
        """,
    )
    m = proc_pattern.match(text)
    if not m:
        return text
    head, args, tail = m.group(1), m.group(2), m.group(3)
    # 按逗号粗略切分（不解析嵌套，因为参数为字面量；够用即可）
    parts = [p.strip() for p in args.split(",")]
    redacted_args = ", ".join(REDACTED for _ in parts)
    return f"{head} {redacted_args}{tail}"


def _sanitize_sp_call(text: str) -> str:
    """SP 调用分支：所有实参全部打掉。"""
    if _RE_SP_EXECUTESQL.match(text):
        return _redact_sp_executesql(text)

    # 优先尝试命名参数替换；若文本中确实存在 @xxx=，就只走这一条
    if re.search(r"@\w+\s*=", text):
        return _redact_named_params(text)

    # 否则按位置参数处理
    return _redact_positional_params(text)


def _sanitize_general_sql(text: str) -> str:
    """普通 SQL 分支：只命中高危敏感模式，不动 SQL 字面量。"""
    # 1. 优先打 password=xxx / token=xxx 这种明确敏感的 KV
    text = _RE_SECRET_KV.sub(lambda m: f"{m.group(1)}={REDACTED}", text)
    # 2. 邮箱
    text = _RE_EMAIL.sub(REDACTED, text)
    # 3. 身份证（先于手机号，避免被手机号正则吃掉前 11 位）
    text = _RE_IDCARD_CN.sub(REDACTED, text)
    # 4. 手机号
    text = _RE_PHONE_CN.sub(REDACTED, text)
    return text


def sanitize_sql_text(text: Optional[str]) -> Optional[str]:
    """对单条 SQL 文本做脱敏。

    - None / 空串：原样返回
    - 以 EXEC/EXECUTE 开头（SP 调用）：所有实参全部替换为 <REDACTED>
    - 其他：仅命中手机号/身份证/邮箱/password= 等高危模式
    - **任何异常**：返回 ``<SANITIZE_FAILED>``，绝不返回原文，避免敏感信息因异常路径泄露
    """
    if not text:
        return text
    # 防御性类型校验：非 str（如 bytes / dict）一律视为脱敏失败，不试图猜测
    if not isinstance(text, str):
        logger.warning("sanitize_sql_text got non-str input: type=%s", type(text).__name__)
        return SANITIZE_FAILED
    try:
        if _RE_EXEC_PREFIX.match(text):
            return _sanitize_sp_call(text)
        return _sanitize_general_sql(text)
    except Exception:
        # 一旦任何正则/字符串处理失败，宁可丢失可读性也不暴露原文
        logger.warning("sanitize_sql_text failed, return placeholder", exc_info=True)
        return SANITIZE_FAILED


def sanitize_rows_sql_text(
    rows: Iterable[Dict[str, Any]],
    fields: Iterable[str] = ("sql_text",),
) -> List[Dict[str, Any]]:
    """批量对 rows 中的指定字段做脱敏（原地修改并返回同一引用列表）。

    单行/单字段独立 try：某一行脱敏失败不影响其他行；失败字段写入
    ``<SANITIZE_FAILED>``，不会保留原文。

    :param rows: DRS 返回的 table_data，每行是 dict
    :param fields: 需要脱敏的字段名集合，默认仅 "sql_text"
    """
    rows_list = list(rows) if not isinstance(rows, list) else rows
    field_tuple = tuple(fields)
    for row in rows_list:
        if not isinstance(row, dict):
            continue
        for f in field_tuple:
            if f not in row:
                continue
            try:
                row[f] = sanitize_sql_text(row.get(f))
            except Exception:
                # sanitize_sql_text 内部已兜底，正常不会到这里；此处再兜一层防御
                logger.warning("sanitize_rows_sql_text failed on field=%s", f, exc_info=True)
                row[f] = SANITIZE_FAILED
    return rows_list
