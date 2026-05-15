# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

清理目标机器上残留的本地 mysql 命令行客户端（通过 socket 文件连接的会话），
避免在主机回收/空闲检查前因为有人忘记退出 mysql 客户端导致后续步骤受阻。

安全策略：
1. 进程名必须严格等于 "mysql"（pgrep -x），不会误伤 mysqld / mysqld_safe /
   mysqldump / mysqlcheck / mysqlbinlog 等其它 mysql 系列工具；
2. 命令行必须同时包含 -S 或 --socket 参数，且包含 .sock 后缀，
   才认定为本地 socket 连接的客户端；
3. 命中即直接 kill -9，无优雅退出阶段；
4. kill 后短暂等待并回查，二次校验 cmdline 后只统计仍残留的目标进程；
5. 没有匹配到任何进程时，脚本 exit 0；若回查仍有目标进程存活，则 exit 1，
   让上层 Pipeline 显式失败，避免遗留客户端干扰后续步骤。
"""
from typing import Dict, List, Optional

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.exec_shell_script import ExecuteShellScriptComponent

CLEAN_LOCAL_MYSQL_CLIENT_SHELL = r"""set +e

# Round 1: match processes whose name is strictly "mysql" (so mysqld / mysqld_safe / mysqldump
# / mysqlcheck / mysqlbinlog will NOT be touched).
killed_pids=""
for pid in $(pgrep -x mysql 2>/dev/null); do
    cmdline=$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)
    [ -z "$cmdline" ] && continue
    # Cmdline must contain both -S/--socket AND a .sock path to be treated as a local socket session.
    if echo "$cmdline" | grep -qE -- '(^|[[:space:]])(-S|--socket)' && echo "$cmdline" | grep -q '\.sock'; then
        echo "[clean_local_mysql_client] kill -9 pid=$pid cmd=[$cmdline]"
        kill -9 "$pid" 2>/dev/null
        killed_pids="$killed_pids $pid"
    fi
done

if [ -z "$killed_pids" ]; then
    echo "[clean_local_mysql_client] no local mysql client process found"
    exit 0
fi

# Give the kernel a brief moment to reap the killed processes.
sleep 1

# Round 2: verify each targeted pid has actually exited; for ones still alive,
# re-check cmdline to defend against PID-reuse false positives.
remaining=""
for pid in $killed_pids; do
    if kill -0 "$pid" 2>/dev/null; then
        cmdline=$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)
        if echo "$cmdline" | grep -qE -- '(^|[[:space:]])(-S|--socket)' && echo "$cmdline" | grep -q '\.sock'; then
            echo "[clean_local_mysql_client] WARN pid=$pid still alive after kill -9, cmd=[$cmdline]"
            remaining="$remaining $pid"
        else
            echo "[clean_local_mysql_client] pid=$pid reused by other process, treat as killed"
        fi
    fi
done

if [ -z "$remaining" ]; then
    echo "[clean_local_mysql_client] verify ok, all killed: $killed_pids"
    exit 0
fi

echo "[clean_local_mysql_client] ERROR still alive pids:$remaining after kill -9"
exit 1
"""


def build_clean_local_mysql_client_sub_process(
    p: Builder, bk_cloud_id: int, iplist: List[str]
) -> Optional[SubProcess]:
    """
    构建"清理本地 mysql 客户端连接"的子流程并返回 SubProcess，不挂载到主流程。
    调用方可自由决定串行 (add_sub_pipeline) 或并行 (add_parallel_sub_pipeline) 编排。
    iplist 为空时返回 None。
    """
    if not iplist:
        return None

    clean_kwargs: Dict[str, object] = {
        "bk_cloud_id": bk_cloud_id,
        "exec_ip": list(iplist),
        "print_ip_log_on_success": True,
        "cluster": {
            "shell_command": CLEAN_LOCAL_MYSQL_CLIENT_SHELL,
        },
    }

    sub_p = SubBuilder(root_id=p.root_id, data=p.data)
    sub_p.add_act(
        act_name=_("清理本地 mysql 客户端连接"),
        act_component_code=ExecuteShellScriptComponent.code,
        kwargs=clean_kwargs,
    )
    return sub_p.build_sub_process(sub_name=_("本地mysql客户端清理"))


def add_clean_local_mysql_client_acts(p: Builder, bk_cloud_id: int, iplist: List[str]) -> None:
    """
    在 pipeline 中串行追加一个子流程，清理目标机器上残留的本地 mysql 客户端连接。

    无进程匹配时脚本以 exit 0 结束，不会影响整体流程。
    iplist 为空时直接跳过。
    """
    sub = build_clean_local_mysql_client_sub_process(p=p, bk_cloud_id=bk_cloud_id, iplist=iplist)
    if sub is not None:
        p.add_sub_pipeline(sub)
