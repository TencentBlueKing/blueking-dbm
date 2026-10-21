# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL 主机进程存活检查 Shell 脚本生成器。

模块职责：
  - 为 revoke 流程"MySQL 主机进程存活检查"场景生成可下发的 bash 脚本
  - 脚本由 dbm-ui 侧 Jinja 渲染 → JobApi.fast_execute_script 下发到目标机器执行
  - 脚本在目标机本地采集 ``ss -Hlntp`` / ``netstat -tnlp`` 输出，扫描所有 LISTEN 行，
    只要命中"MySQL 家族"进程名白名单，即视为"主机上仍有 MySQL 相关进程"
  - 输出结构化 JSON 用 ``<ctx>...</ctx>`` 单行包裹到 stdout，供上层正则提取

设计要点：
  - **主机维度、非实例维度**：上层调用方（revoke 流程）只知道主机 IP，并不知道
    机器上还残留哪些实例端口。因此本脚本**不接收端口列表**，改为"整机扫描 LISTEN 行"
  - **纯函数式**：本模块只提供 ``build_mysql_process_check_script`` 一个入口，
    输入 (expected_proc_names) 得到确定字符串；不做 IO / RPC / DB 调用
  - **目标机零额外依赖**：仅需 ``bash + awk + (ss OR netstat)``，不依赖 Python / jq / dbactor
  - **注入防护**：白名单通过 Jinja 沙箱环境渲染为 bash 数组常量，
    并对进程名做 ``[a-zA-Z0-9_.-]`` 字符白名单校验，阻断 shell 元字符逃逸
  - **awk 兼容性**：解析逻辑用 POSIX awk 语法（``match()`` + ``substr()`` + ``index()``），
    避免使用 gawk 专属的 ``match(str, re, arr)`` 三参数形式；在 mawk / busybox awk 上
    也能正确工作，杜绝"解析失败被误判为 ok"的假阴性
  - **三元组去重**：IPv6 双栈可能让同一 (pid, proc_name) 在多行 LISTEN 中重复出现，
    脚本内部按 ``port|pid|proc_name`` 三元组去重，保持 hits 数组干净
  - **输出契约**：脚本无论 check 结论如何均 ``exit 0``，避免 Job 平台将节点标记为失败
    导致上层拿不到结论；错误信息通过 JSON 的 ``error`` 字段而不是退出码传递

方案语义边界（已知假阴性风险，接受）：
  - **"命名即身份"**：判定基于内核 ``comm`` 字段等值匹配（等值、非子串），
    不做 ``/proc/<pid>/exe`` 路径反查、不做二进制指纹校验；
    若 mysqld 被 rename / exec -a 换 argv[0] 启动，则可能漏判
  - **"快照式检查"**：只看当前 LISTEN 状态，不看 ESTABLISHED / CLOSE_WAIT，
    也不扫描 /proc；若 mysqld 已 crash 但 systemd 正在拉起中的瞬间窗口内，会漏判；
    对该风险的兜底属于上层流程（如"间隔 N 秒采样 2 次"），不属于本脚本
  - 依赖 root 执行权限；脚本内部通过 ``id -u`` 自检并在非 root 时报 ``check_error``
"""
import json
import re
from typing import List, Optional

from jinja2.sandbox import SandboxedEnvironment

#: 默认期望进程名白名单（不明角色兜底）
#:
#: 覆盖 dbm 生态下 MySQL 家族的三种常见 comm 字段值：
#:   - ``mysqld``       —— TenDB / TenDBHA / Spider 后端存储节点
#:   - ``mysql-proxy``  —— TenDBHA 中间件接入层（生产实测 comm 是 ``mysql-proxy`` 而非 ``mysqld-proxy``）
#:   - ``mariadbd``     —— 老版本 MariaDB
#: 生产接入时调用方应按机器角色**收窄**为其中之一，本默认值仅供兜底
DEFAULT_EXPECTED_PROC_NAMES: List[str] = ["mysqld", "mysql-proxy", "mariadbd"]

#: 进程名白名单校验正则；仅允许字母数字、下划线、连字符、点号
#: 禁止空格 / 引号 / ``$`` / 反引号等 shell 元字符，从源头阻断参数注入
_PROC_NAME_RE: re.Pattern = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")

# ==========================================================================
# bash 脚本模板
# --------------------------------------------------------------------------
# 渲染变量：
#   - expected_procs_bash_arr  : bash 数组字面量，如 ("mysqld" "mysql-proxy")
# 脚本执行顺序：
#   1) id -u 权限自检；非 root -> 输出 error JSON 并退 0
#   2) 优先 ss -Hlntp，缺失则 netstat -tnlp；两者都缺 -> 输出 error JSON 并退 0
#   3) awk 逐行解析 LISTEN 行的 users:(("proc",pid=N,fd=M)) 段（POSIX 兼容写法），
#      提取 (port, pid, proc_name)；命中白名单则进入候选
#   4) bash 关联数组按 "port|pid|proc_name" 三元组去重（IPv6 双栈同 pid 场景）
#   5) printf 拼接单行 JSON，用 <ctx>...</ctx> 包裹后写 stdout
# --------------------------------------------------------------------------
_MYSQL_PROCESS_CHECK_SCRIPT_TEMPLATE: str = r"""#!/bin/bash
# =========================================================================
# revoke flow · MySQL host process liveness check script
# (rendered by dbm-ui, DO NOT edit manually)
# Semantics: scan all LISTEN sockets on the whole host; any hit against the
#            "MySQL family" process-name whitelist counts as still-alive.
# Output   : a single-line JSON wrapped in <ctx>...</ctx> on stdout;
#            always exit 0 regardless of the conclusion.
# =========================================================================

# Force C locale so awk / grep / printf behave independently of the host
# locale, avoiding field-parsing differences under non-C locales.
export LC_ALL=C

# Input: expected process-name whitelist (bash array, hard-coded by dbm-ui).
EXPECTED_PROCS=({{ expected_procs_bash_arr }})

# ---------------- helper functions ----------------

# Emit an error JSON and exit 0.
emit_error() {
    local err_msg="$1"
    printf '<ctx>{"found_mysql_procs":false,"hits":[],"collect_tool":null,"error":"%s"}</ctx>\n' "$err_msg"
    exit 0
}

# ---------------- step 1: root privilege self-check ----------------
if [ "$(id -u)" != "0" ]; then
    emit_error "require root to see all processes"
fi

# ---------------- step 2: awk availability self-check ----------------
if ! command -v awk >/dev/null 2>&1; then
    emit_error "awk not available"
fi

# ---------------- step 3: pick the collection tool ----------------
COLLECT_TOOL=""
RAW_LINES=""
if command -v ss >/dev/null 2>&1; then
    COLLECT_TOOL="ss"
    RAW_LINES=$(ss -Hlntp 2>/dev/null)
elif command -v netstat >/dev/null 2>&1; then
    COLLECT_TOOL="netstat"
    # The first two lines of netstat output are headers / descriptions; skip them.
    RAW_LINES=$(netstat -tnlp 2>/dev/null | awk 'NR>2')
else
    emit_error "neither ss nor netstat available"
fi

# ---------------- step 4: parse LISTEN lines with awk ----------------
# Output format (one per line): port<TAB>pid<TAB>proc_name
# Key design points:
#   - Use POSIX awk only: match($0, /re/) returns RSTART/RLENGTH, then
#     slice manually via substr / index. Do NOT rely on gawk's
#     three-argument match(str, re, arr) form.
#   - Extract port from the first digit run after the LAST colon, so that
#     IPv6 addresses (e.g. [::]:3306) don't confuse the parser.
#   - ss "users" segment  : users:(("proc",pid=NNN,fd=MM))
#   - netstat "users" seg : NNN/proc  (last column)
PARSED=$(echo "$RAW_LINES" | awk -v tool="$COLLECT_TOOL" '
{
    if (NF < 4) { next }
    proc_name = ""
    pid = ""
    if (tool == "ss") {
        local_addr = $4
        # Match the whole users:(("proc_name",pid=NNN, segment.
        if (match($0, /users:\(\("[^"]+",pid=[0-9]+,/)) {
            seg = substr($0, RSTART, RLENGTH)
            # seg looks like: users:(("mysqld",pid=19898,
            # Extract proc_name: the text between the first " and the second ".
            q1 = index(seg, "\"")
            if (q1 > 0) {
                rest = substr(seg, q1 + 1)
                q2 = index(rest, "\"")
                if (q2 > 1) {
                    proc_name = substr(rest, 1, q2 - 1)
                }
            }
            # Extract pid: text after "pid=" and before the following ",".
            pi = index(seg, "pid=")
            if (pi > 0) {
                tail = substr(seg, pi + 4)
                ci = index(tail, ",")
                if (ci > 1) {
                    pid = substr(tail, 1, ci - 1)
                }
            }
        }
    } else {
        # netstat: local address is in $4, users segment is the last column,
        # e.g. "12345/mysqld".
        local_addr = $4
        last_field = $NF
        # POSIX-compatible: match first, then split with substr / index.
        if (match(last_field, /^[0-9]+\/./)) {
            sl = index(last_field, "/")
            if (sl > 1) {
                pid = substr(last_field, 1, sl - 1)
                proc_name = substr(last_field, sl + 1)
            }
        }
    }
    # Derive the port from local_addr: digits after the last colon.
    n = split(local_addr, arr, ":")
    port = arr[n]
    # Strip any possible non-digit suffix (e.g. %ifname / brackets); keep digits only.
    gsub(/[^0-9]/, "", port)
    if (port == "" || proc_name == "" || pid == "") { next }
    printf "%s\t%s\t%s\n", port, pid, proc_name
}
')

# ---------------- step 5: whitelist match + triple-dedup, collect hits ----------------
# Build the whitelist lookup table.
declare -A WHITE_SET
for wp in "${EXPECTED_PROCS[@]}"; do
    WHITE_SET[$wp]=1
done

# Triple dedup set: key = "port|pid|proc_name".
declare -A DEDUP_SET

HITS=""
FIRST=1
while IFS=$'\t' read -r p pid proc; do
    [ -z "$p" ] && continue
    [ -z "$proc" ] && continue
    # Keep whitelisted processes only.
    if [ -z "${WHITE_SET[$proc]:-}" ]; then
        continue
    fi
    # Triple dedup.
    dedup_key="${p}|${pid}|${proc}"
    if [ -n "${DEDUP_SET[$dedup_key]:-}" ]; then
        continue
    fi
    DEDUP_SET[$dedup_key]=1

    # JSON string escaping (proc already passed the whitelist, so " / \
    # cannot really appear; the escaping is defensive fallback).
    esc_proc=$(printf '%s' "$proc" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
    entry=$(printf '{"port":%s,"pid":%s,"proc_name":"%s"}' "$p" "$pid" "$esc_proc")
    if [ $FIRST -eq 1 ]; then
        HITS="$entry"
        FIRST=0
    else
        HITS="$HITS,$entry"
    fi
done <<< "$PARSED"

# ---------------- step 6: emit the final <ctx> JSON ----------------
if [ -z "$HITS" ]; then
    FOUND="false"
else
    FOUND="true"
fi
printf '<ctx>{"found_mysql_procs":%s,"hits":[%s],"collect_tool":"%s","error":null}</ctx>\n' \
    "$FOUND" "$HITS" "$COLLECT_TOOL"

exit 0
"""


def _validate_proc_names(expected_proc_names: Optional[List[str]]) -> List[str]:
    """校验进程名白名单并返回规整后的字符串数组。

    :param expected_proc_names: 期望进程名白名单；None / 空 -> 填充 DEFAULT_EXPECTED_PROC_NAMES
    :return: 规整后的 List[str]（去重保序）
    边界：
      - 任一元素不匹配 ``^[A-Za-z0-9_.\\-]{1,64}$`` -> raise ValueError
        （阻断空格 / 引号 / ``$`` / 反引号等 shell 元字符注入）
    """
    if not expected_proc_names:
        return list(DEFAULT_EXPECTED_PROC_NAMES)
    seen: set = set()
    normalized: List[str] = []
    for idx, name in enumerate(expected_proc_names):
        if not isinstance(name, str):
            raise ValueError("expected_proc_names[{}]={!r} is not str".format(idx, name))
        if not _PROC_NAME_RE.match(name):
            raise ValueError(
                "expected_proc_names[{}]={!r} contains disallowed characters; "
                "only [A-Za-z0-9_.-] allowed, length 1..64".format(idx, name)
            )
        if name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def build_mysql_process_check_script(
    expected_proc_names: Optional[List[str]] = None,
) -> str:
    """生成 MySQL 主机进程存活检查的 bash 脚本内容（未 base64 编码）。

    设计要点 / 怎么做：
      - 用 Jinja SandboxedEnvironment 渲染 ``_MYSQL_PROCESS_CHECK_SCRIPT_TEMPLATE``
      - expected_proc_names 渲染为 bash 双引号包裹的字符串数组，如 ``"mysqld" "mysql-proxy"``
      - 渲染前对入参做严格字符白名单校验，阻断 shell 元字符注入
      - **主机维度扫描**：脚本不接收端口列表，整机扫描所有 LISTEN 行，
        命中白名单的进程即计入 hits；上层根据 hits 是否为空判定 ok / mysql_still_alive

    :param expected_proc_names: 允许的进程名白名单；
        None / 空列表 -> 默认 :data:`DEFAULT_EXPECTED_PROC_NAMES`；
        非空时每个元素必须匹配 ``^[A-Za-z0-9_.-]{1,64}$``
    :return: str，完整可执行的 bash 脚本内容；调用方需负责 base64 编码后再交给 JobApi
    边界 / 异常：
      - expected_proc_names 元素含非法字符 -> raise ValueError
      - expected_proc_names 元素非 str -> raise ValueError
      - 目标机器不具备 root 权限执行脚本 -> 脚本内自检并输出 error JSON（本函数无异常）
      - 目标机器同时缺 ss 和 netstat -> 脚本内自检并输出 error JSON

    使用示例::

        from backend.flow.engine.bamboo.scene.mysql.revoke.scripts.mysql_process_check_script import (
            build_mysql_process_check_script,
        )
        # 走默认三件套白名单（mysqld / mysql-proxy / mariadbd）
        script = build_mysql_process_check_script()
        # 或按角色收窄（例如 Storage 节点）
        script = build_mysql_process_check_script(expected_proc_names=["mysqld"])
        # 拷贝到测试机 root 身份 bash -x 复现，或走 JobApi.fast_execute_script 下发
    """
    normalized_procs: List[str] = _validate_proc_names(expected_proc_names)

    # proc names 需要包成双引号；已过字符白名单，安全
    expected_procs_bash_arr: str = " ".join('"{}"'.format(n) for n in normalized_procs)

    # 使用沙箱环境渲染，进一步阻断模板层面的意外表达式执行
    jinja_env = SandboxedEnvironment(
        variable_start_string="{{",
        variable_end_string="}}",
        autoescape=False,
    )
    template = jinja_env.from_string(_MYSQL_PROCESS_CHECK_SCRIPT_TEMPLATE)
    script_content: str = template.render(
        expected_procs_bash_arr=expected_procs_bash_arr,
    )
    return script_content


# 便于外部（HostRevokeChecker.parse_process_check_result）复用的常量：
# 从 <ctx>...</ctx> 提取 JSON 的正则（与既有 dbactor 输出提取正则一致）
CTX_EXTRACT_REGEX: re.Pattern = re.compile(r"<ctx>(?P<context>[\s\S]+?)</ctx>")


def extract_ctx_json(stdout: str) -> Optional[dict]:
    """从脚本 stdout 中提取 ``<ctx>...</ctx>`` 之间的 JSON 并 loads。

    :param stdout: 脚本执行后的完整 stdout 文本
    :return: 成功则返回 dict；失败（无 <ctx> 段 / JSON 非法）返回 None
    边界：
      - stdout 为空或非字符串 -> 返回 None
      - <ctx> 段内容非合法 JSON -> 返回 None
    """
    if not stdout or not isinstance(stdout, str):
        return None
    m = CTX_EXTRACT_REGEX.search(stdout)
    if not m:
        return None
    try:
        return json.loads(m.group("context"))
    except (ValueError, TypeError):
        return None
