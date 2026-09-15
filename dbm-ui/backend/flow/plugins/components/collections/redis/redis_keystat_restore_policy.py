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
import re
from typing import Callable, Dict, List, Tuple

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.components import DRSApi
from backend.db_meta.models.cluster import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.payload_handler import PayloadHandler

MAXMEMORY_POLICY = "maxmemory-policy"
# Flow 元数据门：cluster.major_version 的第一个数字 >= 6 才编排记录/二次确认，并向 actuator 下发 change_maxmemory_policy。
# Actuator 仍用 live INFO Major 再判一次；两边 AND，避免元数据偏低但 live 偏高时改了却无恢复节点。
KEYSTAT_POLICY_MIN_MAJOR = 6


def redis_major_from_version(version: str) -> int:
    """Parse major from cluster.major_version such as Redis-6 / Redis-2.8 / Redis-6.2."""
    match = re.search(r"(\d+)", version or "")
    return int(match.group(1)) if match else 0


def need_keystat_maxmemory_policy_steps(major_version: str) -> bool:
    """元数据门：偏低则不改 maxmemory-policy、不编排恢复相关节点。"""
    return redis_major_from_version(major_version) >= KEYSTAT_POLICY_MIN_MAJOR


def parse_confxx_get_value(result: str, conf_name: str) -> str:
    """从 DRS confxx/CONFIG GET 文本结果里取配置值；找不到 key 返回空，不猜第二行。"""
    lines = [ln.strip() for ln in (result or "").replace("\r", "").split("\n") if ln.strip()]
    name = (conf_name or "").lower()
    for i, ln in enumerate(lines):
        if ln.lower() == name and i + 1 < len(lines):
            return lines[i + 1]
    return ""


def is_unknown_command_err(msg: str) -> bool:
    return "unknown command" in (msg or "").lower()


def get_maxmemory_policies(
    addrs: List[str],
    password: str,
    bk_cloud_id: int,
    redis_rpc: Callable,
) -> Tuple[Dict[str, str], List[str]]:
    """先 confxx get；仅 unknown command 时对该 addr 再试 CONFIG GET。"""
    policies: Dict[str, str] = {}
    errors: List[str] = []
    if not addrs:
        return policies, errors

    confxx_resp = redis_rpc(
        {
            "addresses": addrs,
            "db_num": 0,
            "password": password,
            "command": "confxx get {}".format(MAXMEMORY_POLICY),
            "bk_cloud_id": bk_cloud_id,
        }
    )
    fallback_addrs: List[str] = []
    seen = set()
    for item in confxx_resp or []:
        addr = item.get("address") or ""
        seen.add(addr)
        err_msg = item.get("error_msg") or ""
        if err_msg:
            if is_unknown_command_err(err_msg):
                fallback_addrs.append(addr)
            else:
                errors.append("{}: get {}: {}".format(addr, MAXMEMORY_POLICY, err_msg))
            continue
        policy = parse_confxx_get_value(item.get("result") or "", MAXMEMORY_POLICY)
        if not policy:
            errors.append("{}: get {} empty result".format(addr, MAXMEMORY_POLICY))
            continue
        policies[addr] = policy

    for addr in addrs:
        if addr not in seen and addr not in policies:
            errors.append("{}: get {} no response".format(addr, MAXMEMORY_POLICY))

    if fallback_addrs:
        cfg_resp = redis_rpc(
            {
                "addresses": fallback_addrs,
                "db_num": 0,
                "password": password,
                "command": "CONFIG GET {}".format(MAXMEMORY_POLICY),
                "bk_cloud_id": bk_cloud_id,
            }
        )
        cfg_seen = set()
        for item in cfg_resp or []:
            addr = item.get("address") or ""
            cfg_seen.add(addr)
            if item.get("error_msg"):
                errors.append("{}: CONFIG GET {}: {}".format(addr, MAXMEMORY_POLICY, item["error_msg"]))
                continue
            policy = parse_confxx_get_value(item.get("result") or "", MAXMEMORY_POLICY)
            if not policy:
                errors.append("{}: CONFIG GET {} empty result".format(addr, MAXMEMORY_POLICY))
                continue
            policies[addr] = policy
        for addr in fallback_addrs:
            if addr not in cfg_seen and addr not in policies:
                errors.append("{}: CONFIG GET {} no response".format(addr, MAXMEMORY_POLICY))

    return policies, errors


def inject_keystat_restore_policies(db_act_template: dict, trans_data) -> dict:
    """RedisExecJobComponent2 payload_func：把分析前记录的 policy 注入 actuator payload。"""
    origin = getattr(trans_data, "keystat_origin_maxmemory_policies", None) or {}
    payload = db_act_template.setdefault("payload", {})
    addrs = list(payload.get("addrs") or [])
    if not addrs:
        addrs = [item.get("addr") for item in (payload.get("ins_list") or []) if item.get("addr")]
    missing = [addr for addr in addrs if addr not in origin]
    if missing:
        raise ValueError("no recorded {}: {}".format(MAXMEMORY_POLICY, missing))
    payload["addr_policies"] = {addr: origin[addr] for addr in addrs}
    return db_act_template


def _iter_cluster_addrs(infos: List[Dict]):
    """产出 (cluster, addrs, password, errors)"""
    for info in infos or []:
        cluster_id = info.get("cluster_id")
        addrs = [ins.get("addr") for ins in (info.get("ins") or []) if ins.get("addr")]
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            yield None, addrs, "", ["cluster_id:{} not exist".format(cluster_id)]
            continue
        passwd_ret = PayloadHandler.redis_get_password_by_domain(cluster.immute_domain)
        yield cluster, addrs, passwd_ret.get("redis_password") or "", []


def _get_trans_data(data, kwargs):
    trans_data = data.get_one_of_inputs("trans_data")
    if trans_data is None or trans_data == "${trans_data}":
        trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
    return trans_data


class RedisKeystatRecordPolicyService(BaseService):
    """内存分析前通过 DRS 记录各实例当前的 maxmemory-policy（只读 get）"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = _get_trans_data(data, kwargs)

        origin_policies: Dict[str, str] = {}
        errors: List[str] = []
        for cluster, addrs, password, cluster_errors in _iter_cluster_addrs(kwargs.get("infos") or []):
            if cluster_errors:
                errors.extend(cluster_errors)
                continue
            policies, get_errors = get_maxmemory_policies(
                addrs=addrs, password=password, bk_cloud_id=cluster.bk_cloud_id, redis_rpc=DRSApi.redis_rpc
            )
            errors.extend(get_errors)
            origin_policies.update(policies)
            self.log_info(_("记录 maxmemory-policy, cluster:{}, policies:{}").format(cluster.immute_domain, policies))
        if errors:
            for msg in errors:
                self.log_error(msg)
            return False

        trans_data.keystat_origin_maxmemory_policies = origin_policies
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisKeystatRecordPolicyComponent(Component):
    name = __name__
    code = "redis_keystat_record_policy"
    bound_service = RedisKeystatRecordPolicyService
