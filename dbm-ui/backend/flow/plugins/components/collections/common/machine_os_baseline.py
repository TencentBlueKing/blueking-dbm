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
# hosts_entries 为空时跳过 /etc/hosts；init_ntpdate 为假时跳过时间同步段。
# TencentOS Server 4 用 chronyd，其它发行版走 ntpdate。
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

{% if init_ntpdate %}
echo "refresh dns"
tos -f dns

release=""
if [ -f /etc/tlinux-release ]; then
    release="$(tr -d '\\r' < /etc/tlinux-release | head -n1)"
fi
if [ "${release}" = "TencentOS Server 4" ]; then
    echo "TencentOS Server 4, skip ntpdate, use chronyd"
    systemctl enable --now chronyd
    systemctl is-active --quiet chronyd
    echo "chronyd is active"
else
    NTP_CMD="/bin/sh /usr/local/ieod-public/ntpdate/ntpdate.sh --maxoffset 3"
    current_cron="$(crontab -l 2>/dev/null || true)"
    if printf '%s\\n' "${current_cron}" | grep -F -- "${NTP_CMD}" >/dev/null; then
        echo "ntp crontab already exists, skip"
    else
        minute=$((RANDOM % 60))
        line="${minute} * * * * ${NTP_CMD}"
        {
            printf '%s\\n' "${current_cron}"
            echo "${line}"
        } | sed '/^$/d' | crontab -
        echo "ntp crontab added: ${line}"
    fi

    echo "force ntpdate"
    /bin/sh /usr/local/ieod-public/ntpdate/ntpdate.sh -f
fi
{% else %}
echo "INIT_OS_NTPDATE disabled, skip ntpdate"
{% endif %}

echo "machine os init done"
"""  # noqa


def init_ntpdate_enabled() -> bool:
    """系统配置 INIT_OS_NTPDATE 为 true 时才初始化时间同步。缺省或未登记视为关闭。"""
    from backend.configuration.constants import SystemSettingsEnum
    from backend.configuration.models import SystemSettings

    return SystemSettings.get_setting_value(key=SystemSettingsEnum.INIT_OS_NTPDATE.value, default=False) is True


def render_machine_os_baseline_script(hosts_entries: Optional[List[dict]] = None, init_ntpdate: bool = False) -> str:
    """渲染主机 OS 初始化脚本。hosts 为空跳过 hosts 段，init_ntpdate 为假跳过时间同步段。"""
    jinja_env = Environment()
    template = jinja_env.from_string(MACHINE_OS_BASELINE_SCRIPT)
    return template.render(hosts_entries=hosts_entries or [], init_ntpdate=bool(init_ntpdate))


def build_machine_os_baseline_acts(host_list: Optional[List[dict]], hosts_entries: Optional[List[dict]]) -> List[dict]:
    """按 bk_cloud_id 生成「主机OS初始化」act。

    host_list 为空（海磊补货在编排期还没有机器）时仍返回一个 act，
    执行期由组件从 trans_data.hosts 补齐目标。
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
                # 作业成功后把每台机器的脚本 stdout 打进 flow 日志
                "print_ip_log_on_success": True,
            },
        }

    if not grouped:
        return [_one([])]
    return [_one(targets) for targets in grouped.values()]


class MachineOsBaselineService(BkJobService):
    """入资源池前的主机 OS 初始化。

    同一 Job 脚本顺序执行，任一步失败则节点失败：
    1. 按 hosts_entries 幂等追加 /etc/hosts（为空则跳过）
    2. INIT_OS_NTPDATE 开启时：tos -f dns；TencentOS Server 4 启用 chronyd，否则 ntpdate crontab + ntpdate.sh -f

    kwargs:
        exec_targets  list[{"ip": str, "bk_cloud_id": int}]
                      编排期已知的目标机。为空时从 trans_data.hosts 补齐（海磊补货）。
        hosts_entries list[{"ip": str, "domain": str}]
                      INIT_OS_HOSTS 转换后的条目，可为空。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")

        exec_targets = list(kwargs.get("exec_targets") or [])
        hosts_entries = kwargs.get("hosts_entries") or []
        init_ntpdate = init_ntpdate_enabled()

        if not init_ntpdate and not hosts_entries:
            self.log_info(_("INIT_OS_NTPDATE 未开启且无 hosts 条目，跳过主机OS初始化"))
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

        script_content = render_machine_os_baseline_script(hosts_entries, init_ntpdate=init_ntpdate)
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
        self.log_info(_("hosts 条目数: {}，INIT_OS_NTPDATE: {}").format(len(hosts_entries), init_ntpdate))

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
