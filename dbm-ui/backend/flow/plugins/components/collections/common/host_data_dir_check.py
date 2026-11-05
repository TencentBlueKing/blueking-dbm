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
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

from django.utils.translation import gettext as _
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

# for/glob stays in this shell on bash 3.2 and later. A find|while pipeline
# runs the loop in a subshell unless lastpipe is on, and bash 4.1 has no lastpipe.
HOST_DATA_DIR_CHECK_SCRIPT_TEMPLATE = r"""#!/bin/bash
export LC_ALL=C
SCAN_ROOT=/
failed=0
reported=0
report_limit=50

report() {
    failed=1
    if [ "$reported" -lt "$report_limit" ]; then
        printf '%s: %s: %s\n' __Q_ERROR__ "$1" "$2"
    elif [ "$reported" -eq "$report_limit" ]; then
        printf '%s %s\n' __Q_OMITTED__ "$report_limit"
    fi
    reported=$((reported + 1))
}

check_allow_empty() {
    local dir="$1" entry base pat exempt
    shift
    if [ ! -d "$dir" ] || [ ! -r "$dir" ] || [ ! -x "$dir" ]; then
        report __Q_NOT_DIR__ "$dir"
        return
    fi
    for entry in "$dir"/* "$dir"/.[!.]* "$dir"/..?*; do
        [ -e "$entry" ] || [ -L "$entry" ] || continue
        base=${entry##*/}
        exempt=0
        if [ -d "$entry" ] && [ ! -L "$entry" ]; then
            for pat in "$@"; do
                case "$base" in
                    $pat) exempt=1 ;;
                esac
            done
        fi
        if [ "$exempt" -eq 0 ]; then
            report __Q_ENTRY__ "$entry"
            return
        fi
    done
}

if [ ! -d "$SCAN_ROOT" ] || [ ! -r "$SCAN_ROOT" ] || [ ! -x "$SCAN_ROOT" ]; then
    report __Q_ROOT__ "$SCAN_ROOT"
    exit 1
fi

for data_dir in "$SCAN_ROOT"/*; do
    [ -e "$data_dir" ] || [ -L "$data_dir" ] || continue
    name=${data_dir##*/}
    case "$name" in
        data*) ;;
        *) continue ;;
    esac
    suffix=${name#data}
    case "$suffix" in
        *[!0-9]*) continue ;;
    esac
    if [ ! -d "$data_dir" ] || [ ! -r "$data_dir" ] || [ ! -x "$data_dir" ]; then
        report __Q_DATA__ "$data_dir"
        continue
    fi
    for candidate in "$data_dir"/* "$data_dir"/.[!.]* "$data_dir"/..?*; do
        [ -e "$candidate" ] || [ -L "$candidate" ] || continue
        base=${candidate##*/}
        case "$base" in
__CASE_ARMS__
        esac
    done
done

if [ "$failed" -ne 0 ]; then
    printf '%s\n' __Q_FAIL__
    exit 1
fi
printf '%s\n' __Q_OK__
"""

_CASE_PATTERN_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.*-")


def _shell_case_pattern(pattern: str) -> str:
    if not pattern or any(char not in _CASE_PATTERN_CHARS for char in pattern):
        raise ValueError(_("残留数据目录检查的匹配模式无效: {}").format(pattern))
    return pattern


def _sh_quote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def render_host_data_dir_check_script() -> str:
    arms = []
    residual = _sh_quote(_("残留路径仍在"))
    for rule in HOST_DATA_DIR_CHECK_RULES:
        pattern = _shell_case_pattern(rule.pattern)
        if rule.allow_empty:
            quoted_exempt = " ".join("'{}'".format(_shell_case_pattern(item)) for item in rule.exempt_dir_patterns)
            body = '            check_allow_empty "$candidate" {}'.format(quoted_exempt).rstrip()
        else:
            body = '            report {} "$candidate"'.format(residual)
        arms.append("        {pattern})\n{body}\n            ;;".format(pattern=pattern, body=body))
    script = HOST_DATA_DIR_CHECK_SCRIPT_TEMPLATE.replace("__CASE_ARMS__", "\n".join(arms))
    messages = {
        "__Q_ERROR__": _sh_quote(_("错误")),
        "__Q_OMITTED__": _sh_quote(_("错误: 其余结果已省略，上限")),
        "__Q_NOT_DIR__": _sh_quote(_("路径不是可访问的目录")),
        "__Q_ROOT__": _sh_quote(_("无法访问文件系统根目录")),
        "__Q_DATA__": _sh_quote(_("数据路径不是可访问的目录")),
        "__Q_ENTRY__": _sh_quote(_("存在未豁免的目录项")),
        "__Q_FAIL__": _sh_quote(_("错误: 残留目录检查未通过，请先处理未豁免路径再重试")),
        "__Q_OK__": _sh_quote(_("通过: 没有未豁免的残留路径")),
    }
    for placeholder, quoted in messages.items():
        script = script.replace(placeholder, quoted)
    return script


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
