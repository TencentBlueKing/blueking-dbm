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
import logging
import re

from django.utils import timezone

from backend.components import JobApi
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.utils.string import base64_encode

logger = logging.getLogger("root")

_SET_LINE_RE = re.compile(r"^set\s+[+-]", re.ASCII)


def _inject_after_script_header(script: str, injection: str) -> str:
    lines = script.splitlines(keepends=True)
    i = 0

    if lines and lines[0].lstrip().startswith("#!"):
        i = 1

    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#") or _SET_LINE_RE.match(stripped):
            i += 1
            continue
        break

    block = injection if injection.endswith("\n") else f"{injection}\n"
    lines.insert(i, block)
    return "".join(lines)


def execute_script(
    name: str,
    username: str,
    bk_cloud_id: int,
    ips: list[str],
    script: str,
    run_as: str,
    bk_scope_type: str,
    bk_scope_id: str,
) -> int:
    nginx = DBExtension.get_extension_in_cloud(bk_cloud_id=bk_cloud_id, extension_type=ExtensionType.NGINX.value)
    nginx_ips = [n.details["ip"] for n in nginx]
    if not nginx_ips:
        raise DBMMcpBaseException(msg=f"query bk_cloud_id: {bk_cloud_id} nginx failed")

    nginx_ip_list = " ".join(nginx_ips)
    export_env_local_ip_script = (
        f"export LOCAL_IP=$(for ip in {nginx_ip_list}; do "
        f's=$(ip -o route get "$ip" 2>/dev/null | awk \'{{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}}\'); '
        f'[ -n "$s" ] && {{ echo "$s"; break; }}; done)\n'
        f'[ -z "$LOCAL_IP" ] && exit 1\n'
    )
    script = _inject_after_script_header(script, export_env_local_ip_script)

    body = {
        "bk_scope_type": bk_scope_type,
        "bk_scope_id": bk_scope_id,
        "task_name": f"{username}_{name}_{timezone.localtime().strftime('%Y%m%d%H%M%S')}",
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": [{"bk_cloud_id": bk_cloud_id, "ip": ip} for ip in ips]},
        "account_alias": run_as,
    }
    logger.info(f"body: {body}")
    resp = JobApi.fast_execute_script(body, raw=True, use_admin=False, use_param_user=username)
    logger.info(f"resp: {resp}")
    if resp.get("code") != 0 or not resp.get("result"):
        raise DBMMcpBaseException(msg=resp.get("message") or "fast_execute_script failed")
    return resp["data"]["job_instance_id"]
