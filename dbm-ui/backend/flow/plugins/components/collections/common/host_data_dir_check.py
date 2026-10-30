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
import copy
import ipaddress
import shlex
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

from django.utils.translation import gettext as _
from jinja2.sandbox import SandboxedEnvironment as Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode


@dataclass(frozen=True)
class HostDataDirCheckRule:
    """数据盘下的直接条目规则；豁免仅适用于允许为空的目录内的直接子目录。"""

    pattern: str
    allow_empty: bool = False
    exempt_dir_patterns: Tuple[str, ...] = ()


HOST_DATA_DIR_CHECK_RULES = (
    HostDataDirCheckRule(pattern="mysqldata"),
    HostDataDirCheckRule(pattern="mysqllog"),
    HostDataDirCheckRule(pattern="mysqldata_*"),
    HostDataDirCheckRule(pattern="mysqllog_*"),
    HostDataDirCheckRule(pattern="dbbak", allow_empty=True, exempt_dir_patterns=("force.shutdown.*",)),
)

HOST_DATA_DIR_CHECK_SCRIPT_TEMPLATE = r"""#!/bin/bash
set -euo pipefail
export LC_ALL=C
SCAN_ROOT=/
failed=0
reported=0
report_limit=50

report_error() {
    failed=1
    if (( reported < report_limit )); then
        printf 'ERROR: %s: %q\n' "$1" "$2"
    elif (( reported == report_limit )); then
        printf 'ERROR: further findings omitted (limit %s)\n' "$report_limit"
    fi
    reported=$((reported + 1))
}

check_candidate() {
    local candidate="$1" pattern="$2" allow_empty="$3" entry
    shift 3
    [[ "${candidate##*/}" == $pattern ]] || return 0
    if [[ "$allow_empty" == 0 ]]; then
        report_error 'residual path remains' "$candidate"
        return
    fi
    if [[ ! -d "$candidate" || ! -r "$candidate" || ! -x "$candidate" ]]; then
        report_error 'path is not an accessible directory' "$candidate"
        return
    fi
    local -a exempt_names=(-false)
    for pattern in "$@"; do
        exempt_names+=(-o -name "$pattern")
    done
    if entry=$(find -H "$candidate" -mindepth 1 -maxdepth 1 \
        ! \( -type d \( "${exempt_names[@]}" \) \) -printf '%p/' -quit); then
        if [[ -n "$entry" ]]; then
            report_error 'non-exempt directory entry remains' "${entry%/}"
        fi
    else
        report_error 'cannot inspect directory' "$candidate"
    fi
}

if [[ ! -d "$SCAN_ROOT" || ! -r "$SCAN_ROOT" || ! -x "$SCAN_ROOT" ]]; then
    report_error 'cannot access filesystem root' "$SCAN_ROOT"
    exit 1
fi

exec 3< <(find -H "$SCAN_ROOT" -mindepth 1 -maxdepth 1 -name 'data*' -print0)
root_scan_pid=$!
while IFS= read -r -d '' data_dir <&3; do
    [[ "${data_dir##*/}" =~ ^data[0-9]*$ ]] || continue
    if [[ ! -d "$data_dir" || ! -r "$data_dir" || ! -x "$data_dir" ]]; then
        report_error 'data path is not an accessible directory' "$data_dir"
        continue
    fi
    exec 4< <(find -H "$data_dir" -mindepth 1 -maxdepth 1 \
        \( -false{% for rule in rules %} -o -name {{ rule.pattern | shellquote }}{% endfor %} \) -print0)
    data_scan_pid=$!
    while IFS= read -r -d '' candidate <&4; do
{% for rule in rules %}
        check_candidate "$candidate" {{ rule.pattern | shellquote }} {{ 1 if rule.allow_empty else 0 }} \
            {{ rule.exempt_dir_patterns | map('shellquote') | join(' ') }}
{% endfor %}
    done
    exec 4<&-
    if ! wait "$data_scan_pid"; then
        report_error 'cannot scan data directory' "$data_dir"
    fi
done
exec 3<&-
if ! wait "$root_scan_pid"; then
    report_error 'cannot enumerate data directories' "$SCAN_ROOT"
fi

if (( failed )); then
    printf 'ERROR: residual directory check failed; resolve non-exempt paths before retrying\n'
    exit 1
fi
printf 'OK: no non-exempt residual paths; configured directory exemptions applied\n'
"""


def render_host_data_dir_check_script() -> str:
    jinja_env = Environment()
    jinja_env.filters["shellquote"] = shlex.quote
    return jinja_env.from_string(HOST_DATA_DIR_CHECK_SCRIPT_TEMPLATE).render(rules=HOST_DATA_DIR_CHECK_RULES)


def _normalize_targets(hosts: List[dict]) -> List[dict]:
    if not isinstance(hosts, list):
        raise ValueError(_("残留数据目录检查的主机列表格式错误"))
    targets, seen = [], set()
    for host in hosts:
        if not isinstance(host, dict):
            raise ValueError(_("残留数据目录检查的主机信息格式错误: {}").format(host))
        ip = host.get("ip")
        cloud_id = host.get("bk_cloud_id", 0)
        if not isinstance(ip, str):
            raise ValueError(_("残留数据目录检查的主机 IP 无效: {}").format(ip))
        try:
            ipaddress.ip_address(ip)
        except ValueError as err:
            raise ValueError(_("残留数据目录检查的主机 IP 无效: {}").format(ip)) from err
        if isinstance(cloud_id, str) and cloud_id.isdecimal():
            cloud_id = int(cloud_id)
        if type(cloud_id) is not int or cloud_id < 0:
            raise ValueError(_("残留数据目录检查的管控区域无效: {}").format(cloud_id))
        key = (cloud_id, ip)
        if key not in seen:
            seen.add(key)
            targets.append({"ip": ip, "bk_cloud_id": cloud_id})
    return targets


def build_host_data_dir_check_acts(host_list: Optional[List[dict]]) -> List[dict]:
    """按云区域构建检查节点，HCM 编排期没有主机时保留运行期补齐节点。"""
    grouped = defaultdict(list)
    for target in _normalize_targets(host_list if host_list is not None else []):
        grouped[target["bk_cloud_id"]].append(target)
    return [
        {
            "act_name": _("检查主机残留数据目录"),
            "act_component_code": HostDataDirResidualCheckComponent.code,
            "kwargs": {"exec_targets": targets, "print_ip_log_on_success": True},
        }
        for targets in (list(grouped.values()) or [[]])
    ]


class HostDataDirResidualCheckService(BkJobService):
    """资源入池前检查数据目录，只读并豁免 dbbak 下的 force.shutdown.* 目录。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        targets = kwargs.get("exec_targets", [])
        if targets == []:
            trans_data = data.get_one_of_inputs("trans_data")
            if isinstance(trans_data, dict):
                targets = trans_data.get("hosts", [])
        try:
            targets = _normalize_targets(targets)
        except ValueError as err:
            self.log_error(str(err))
            return False
        if not targets:
            self.log_error(_("执行目标为空，且上下文中没有主机，无法检查残留数据目录"))
            return False

        self.log_info(_("准备检查主机残留数据目录，目标机器: {}").format(targets))
        self.log_info(_("残留数据目录检查规则: {}").format([asdict(rule) for rule in HOST_DATA_DIR_CHECK_RULES]))
        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM-Host-Data-Dir-Check",
            "script_content": base64_encode(render_host_data_dir_check_script()),
            "script_language": 1,
            "target_server": {"ip_list": targets},
        }
        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs.update(account_alias=DBA_ROOT_USER, timeout=300)
        data.outputs.ext_result = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        data.outputs.exec_ips = targets
        return True


class HostDataDirResidualCheckComponent(Component):
    name = __name__
    code = "host_data_dir_check"
    bound_service = HostDataDirResidualCheckService
