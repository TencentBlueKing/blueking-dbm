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
from collections import defaultdict
from typing import Dict, List, Optional

from django.utils.translation import gettext as _
from jinja2.sandbox import SandboxedEnvironment as Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

# 入资源池前的主机 OS 初始化脚本。后续步骤追加在同一脚本里，不要为此再拆 act。
# hosts_entries 为空时跳过 /etc/hosts；init_timesync 为假时跳过时间同步段。
# chronyd / tos 失败只打 WARN。走 ntpdate 时脚本不存在或 ntpdate.sh -f 失败则退出。
# TencentOS / tlinux 主版本 >= 3 用 chronyd（并 tos -f dns），其它走 ntpdate，不刷 DNS。
MACHINE_OS_BASELINE_SCRIPT = """
#!/bin/bash
set -euo pipefail

{% if hosts_entries %}
BAK_FILE="/etc/hosts.bak.$(date +%Y%m%d%H%M%S)"
cp -f /etc/hosts "${BAK_FILE}"
echo "backed up /etc/hosts to ${BAK_FILE}"

{% for entry in hosts_entries %}
HOSTS_ENTRY="{{ entry.ip }} {{ entry.domain }}"
if grep -qF "${HOSTS_ENTRY}" /etc/hosts; then
    echo "entry already exists, skip: ${HOSTS_ENTRY}"
else
    echo "${HOSTS_ENTRY}" >> /etc/hosts
    echo "entry added: ${HOSTS_ENTRY}"
fi
{% endfor %}

echo "update /etc/hosts done"
{% else %}
echo "hosts entries empty, skip /etc/hosts"
{% endif %}

{% if init_timesync %}
release=""
os_id=""
version_id=""
if [ -f /etc/os-release ]; then
    os_id="$(awk -F= '/^ID=/{gsub(/"/,"",$2); gsub(/\\r/,""); print $2; exit}' /etc/os-release)"
    version_id="$(awk -F= '/^VERSION_ID=/{gsub(/"/,"",$2); gsub(/\\r/,""); print $2; exit}' /etc/os-release)"
    release="$(awk -F= '/^PRETTY_NAME=/{gsub(/"/,"",$2); gsub(/\\r/,""); print $2; exit}' /etc/os-release)"
fi
if [ -z "${release}" ] && [ -f /etc/tlinux-release ]; then
    release="$(awk 'NR==1{gsub(/\\r/,""); print; exit}' /etc/tlinux-release)"
fi
os_major=""
if [ -n "${version_id}" ]; then
    os_major="${version_id%%.*}"
else
    os_major="$(printf '%s\\n' "${release}" | awk 'match($0, /[0-9]+/){print substr($0, RSTART, RLENGTH); exit}')"
fi
use_chrony=0
case "$(printf '%s %s' "${os_id}" "${release}")" in
    *tencentos*|*TencentOS*|*tlinux*|*Tlinux*)
        case "${os_major}" in
            ''|*[!0-9]*) ;;
            *)
                if [ "${os_major}" -ge 3 ]; then
                    use_chrony=1
                fi
                ;;
        esac
        ;;
esac
if [ "${use_chrony}" -eq 1 ]; then
    echo "TencentOS ${os_major}, skip ntpdate, use chronyd (${release})"
    echo "refresh dns"
    if command -v tos >/dev/null 2>&1; then
        tos -f dns || echo "WARN: tos -f dns failed, continue"
    else
        echo "WARN: tos not found, skip dns refresh"
    fi
    systemctl enable --now chronyd || echo "WARN: systemctl enable --now chronyd failed, continue"
    if systemctl is-active --quiet chronyd; then
        echo "chronyd is active"
    else
        echo "WARN: chronyd is not active, continue"
    fi
else
    NTP_SH="/usr/local/ieod-public/ntpdate/ntpdate.sh"
    if [ ! -f "${NTP_SH}" ]; then
        echo "ERROR: ${NTP_SH} not found"
        exit 1
    fi
    echo "force ntpdate"
    /bin/sh "${NTP_SH}" -f || { echo "ERROR: ${NTP_SH} -f failed"; exit 1; }

    NTP_CMD="/bin/sh ${NTP_SH} --maxoffset 3"
    CRON_BAK="/tmp/crontab.bak.$(date +%Y%m%d%H%M%S)"
    CRON_ERR="${CRON_BAK}.err"
    update_cron=1
    current_cron=""
    if crontab -l > "${CRON_BAK}" 2>"${CRON_ERR}"; then
        echo "crontab backed up to ${CRON_BAK}"
        rm -f "${CRON_ERR}"
        current_cron="$(cat "${CRON_BAK}")"
    else
        cron_err="$(cat "${CRON_ERR}" 2>/dev/null || true)"
        rm -f "${CRON_BAK}" "${CRON_ERR}"
        if printf '%s\\n' "${cron_err}" | grep -qi "no crontab"; then
            echo "no existing crontab"
        else
            echo "WARN: crontab -l failed (${cron_err}), skip ntp crontab update"
            update_cron=0
        fi
    fi
    if [ "${update_cron}" -eq 1 ]; then
        if printf '%s\\n' "${current_cron}" | grep -F -- "${NTP_CMD}" >/dev/null; then
            echo "ntp crontab already exists, skip"
        else
            minute=$((RANDOM % 60))
            line="${minute} * * * * ${NTP_CMD}"
            if [ -n "${current_cron}" ]; then
                cron_body="$(printf '%s\\n%s\\n' "${current_cron}" "${line}")"
            else
                cron_body="$(printf '%s\\n' "${line}")"
            fi
            if printf '%s\\n' "${cron_body}" | crontab -; then
                echo "ntp crontab added: ${line}"
            else
                echo "WARN: crontab update failed, continue"
            fi
        fi
    fi
fi
{% else %}
echo "INIT_OS_TIMESYNC disabled, skip timesync"
{% endif %}

echo "machine os init done"
"""  # noqa

# JSONField 不做类型转换，admin/API 可能写成字符串或数字。
_TIMESYNC_TRUE_STRINGS = ("true", "1", "on", "yes")


def init_timesync_enabled() -> bool:
    """系统配置 INIT_OS_TIMESYNC 开启时才初始化时间同步。缺省或未登记视为关闭。"""
    from backend.configuration.constants import SystemSettingsEnum
    from backend.configuration.models import SystemSettings

    raw = SystemSettings.get_setting_value(key=SystemSettingsEnum.INIT_OS_TIMESYNC.value, default=False)
    if isinstance(raw, str):
        return raw.strip().lower() in _TIMESYNC_TRUE_STRINGS
    return bool(raw)


def render_machine_os_baseline_script(hosts_entries: Optional[List[dict]] = None, init_timesync: bool = False) -> str:
    """渲染主机 OS 初始化脚本。hosts 为空跳过 hosts 段，init_timesync 为假跳过时间同步段。"""
    jinja_env = Environment()
    template = jinja_env.from_string(MACHINE_OS_BASELINE_SCRIPT)
    return template.render(hosts_entries=hosts_entries or [], init_timesync=bool(init_timesync))


def build_machine_os_baseline_acts(
    host_list: Optional[List[dict]],
    hosts_entries: Optional[List[dict]],
    init_timesync: bool = False,
) -> List[dict]:
    """按 bk_cloud_id 生成「主机OS初始化」act。

    host_list 为空（HCM 补货在编排期还没有机器）时仍返回一个 act，
    执行期由组件从 trans_data.hosts 补齐目标。
    init_timesync 使用编排期快照，执行期不再读库。
    """
    grouped: Dict[int, List[dict]] = defaultdict(list)
    for host in host_list or []:
        cloud_id = host.get("bk_cloud_id", 0)
        grouped[cloud_id].append({"ip": host["ip"], "bk_cloud_id": cloud_id})

    def _one(targets: List[dict]) -> dict:
        return {
            "act_name": _("主机OS初始化"),
            "act_component_code": MachineOsBaselineComponent.code,
            "kwargs": {
                "exec_targets": targets,
                "hosts_entries": hosts_entries or [],
                "init_timesync": bool(init_timesync),
                # 作业成功后把每台机器的脚本 stdout 打进 flow 日志
                "print_ip_log_on_success": True,
            },
        }

    if not grouped:
        return [_one([])]
    return [_one(targets) for targets in grouped.values()]


class MachineOsBaselineService(BkJobService):
    """入资源池前的主机 OS 初始化。

    同一 Job 脚本顺序执行：
    1. 按 hosts_entries 幂等追加 /etc/hosts（为空则跳过）。这一步失败则节点失败。
    2. kwargs.init_timesync 为真时做时间同步：TencentOS / tlinux 主版本 >= 3 时
       tos -f dns 并启用 chronyd，失败只打 WARN。其它系统走 ntpdate.sh -f 再写 crontab，不刷 DNS。
       ntpdate.sh 不存在或 ntpdate.sh -f 失败则节点失败；crontab 写入失败只打 WARN。

    kwargs:
        exec_targets  list[{"ip": str, "bk_cloud_id": int}]
                      编排期已知的目标机。为空时从 trans_data.hosts 补齐（HCM 补货）。
        hosts_entries list[{"ip": str, "domain": str}]
                      INIT_OS_HOSTS 转换后的条目，可为空。
        init_timesync  bool
                      编排期 INIT_OS_TIMESYNC 快照。执行期只读这里，不再查库。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")

        exec_targets = list(kwargs.get("exec_targets") or [])
        hosts_entries = kwargs.get("hosts_entries") or []
        init_timesync = bool(kwargs.get("init_timesync"))

        if not init_timesync and not hosts_entries:
            self.log_info(_("INIT_OS_TIMESYNC 未开启且无 hosts 条目，跳过主机OS初始化"))
            data.outputs.ext_result = True
            return True

        # 编排期没有机器时才用运行期上下文，避免按云区域拆开的 act 互相吞掉全部主机
        if not exec_targets and isinstance(trans_data, dict) and trans_data.get("hosts"):
            exec_targets = [
                {"ip": host["ip"], "bk_cloud_id": host.get("bk_cloud_id", 0)} for host in trans_data["hosts"]
            ]

        exec_targets = _dedupe_targets(exec_targets)
        if not exec_targets:
            self.log_error(_("exec_targets 为空，且上下文中没有主机，无法执行主机OS初始化"))
            return False

        script_content = render_machine_os_baseline_script(hosts_entries, init_timesync=init_timesync)
        target_ip_info = [{"bk_cloud_id": target["bk_cloud_id"], "ip": target["ip"]} for target in exec_targets]

        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM-Machine-Os-Init",
            "script_content": base64_encode(script_content),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info(_("准备执行主机OS初始化，目标机器数: {}").format(len(target_ip_info)))
        self.log_info(_("hosts 条目数: {}，INIT_OS_TIMESYNC: {}").format(len(hosts_entries), init_timesync))

        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER

        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")
        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")

        data.outputs.ext_result = resp
        data.outputs.exec_ips = [{"ip": target["ip"], "bk_cloud_id": target["bk_cloud_id"]} for target in exec_targets]
        return True


def _dedupe_targets(exec_targets: List[dict]) -> List[dict]:
    seen = set()
    deduped = []
    for target in exec_targets:
        ip = target.get("ip")
        if not ip:
            continue
        cloud_id = target.get("bk_cloud_id", 0)
        key = (ip, cloud_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append({"ip": ip, "bk_cloud_id": cloud_id})
    return deduped


class MachineOsBaselineComponent(Component):
    """主机 OS 初始化。后续步骤追加到同一脚本，不另开节点。"""

    name = __name__
    code = "machine_os_baseline"
    bound_service = MachineOsBaselineService
