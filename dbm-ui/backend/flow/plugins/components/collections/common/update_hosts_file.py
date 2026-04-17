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

from django.utils.translation import gettext as _
from jinja2.sandbox import SandboxedEnvironment as Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

# /etc/hosts 更新脚本模板（Jinja2）
# 参数：
#   hosts_entries - list[{"ip": str, "domain": str}]，要写入的 hosts 条目列表
#
# 逻辑：
#   1. 备份 /etc/hosts 到 /etc/hosts.bak.<时间戳>（每次执行只备份一次）
#   2. 逐条检查条目是否已存在，不存在则追加写入（幂等）
update_hosts_script = """
#!/bin/bash
set -e

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
"""  # noqa


class AddHostsEntryService(BkJobService):
    """
    在目标机器的 /etc/hosts 中写入指定条目。

    写入前先备份原文件，逐条检查是否已存在（幂等），仅追加缺失的条目。

    kwargs 说明：
        exec_targets  list[{"ip": str, "bk_cloud_id": int}]
                      目标机器列表，每台机器携带自己所属的管控区域 ID，
                      不能使用统一的 bk_cloud_id，避免混合管控区域时执行错误。
        hosts_entries list[{"ip": str, "domain": str}]
                      要写入 /etc/hosts 的条目列表，由调用方（flow builder）
                      从系统配置 INIT_OS_HOSTS 读取并转换后传入，
                      Component 本身不硬编码任何条目值。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        exec_targets = kwargs.get("exec_targets", [])
        hosts_entries = kwargs.get("hosts_entries", [])

        # 从上下文中补充目标机器（HCM流程中主机在运行时动态申请，build时exec_targets为空）
        if isinstance(trans_data, dict) and trans_data.get("hosts"):
            trans_targets = [{"ip": h["ip"], "bk_cloud_id": h.get("bk_cloud_id", 0)} for h in trans_data["hosts"]]
            exec_targets = trans_targets + exec_targets
            # 按 (ip, bk_cloud_id) 去重，保留首次出现的条目
            seen = set()
            deduped = []
            for t in exec_targets:
                key = (t["ip"], t["bk_cloud_id"])
                if key not in seen:
                    seen.add(key)
                    deduped.append(t)
            exec_targets = deduped

        if not exec_targets:
            self.log_error(_("exec_targets 参数为空，无目标机器可执行"))
            return False

        if not hosts_entries:
            self.log_error(_("hosts_entries 参数为空，无需写入任何条目"))
            return False

        # 渲染 Jinja2 脚本，将 hosts 条目列表注入模板
        jinja_env = Environment()
        template = jinja_env.from_string(update_hosts_script)
        script_content = template.render(hosts_entries=hosts_entries)

        # 每台机器使用自己所属的管控区域 ID（bk_cloud_id），
        # 不能共用同一个值，否则不同管控区域的机器会执行到错误目标
        target_ip_info = [{"bk_cloud_id": t["bk_cloud_id"], "ip": t["ip"]} for t in exec_targets]

        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM-Update-Hosts-File",
            "script_content": base64_encode(script_content),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info(_("准备更新 /etc/hosts，目标机器数: {}").format(len(target_ip_info)))
        self.log_info(_("待写入条目: {}").format(hosts_entries))

        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER

        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")
        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")

        data.outputs.ext_result = resp
        # exec_ips 必须存为 {"ip": ..., "bk_cloud_id": ...} 的 dict 列表，
        # 而不是纯字符串列表，否则 BkJobService._schedule 在轮询阶段会
        # 回退读 kwargs["bk_cloud_id"]（兼容旧代码路径），导致 KeyError。
        data.outputs.exec_ips = [{"ip": t["ip"], "bk_cloud_id": t["bk_cloud_id"]} for t in exec_targets]
        return True


class AddHostsEntryComponent(Component):
    name = __name__
    code = "add_hosts_entry"
    bound_service = AddHostsEntryService
