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
# 与 actuator keystat.go 一致：Major >= 6 才会改 maxmemory-policy 以带上 atime
KEYSTAT_POLICY_MIN_MAJOR = 6


def redis_major_from_version(version: str) -> int:
    """Parse major from cluster.major_version such as Redis-6 / Redis-2.8 / Redis-6.2."""
    match = re.search(r"(\d+)", version or "")
    return int(match.group(1)) if match else 0


def need_keystat_maxmemory_policy_steps(major_version: str) -> bool:
    return redis_major_from_version(major_version) >= KEYSTAT_POLICY_MIN_MAJOR


def parse_confxx_get_value(result: str, conf_name: str) -> str:
    lines = [ln.strip() for ln in (result or "").replace("\r", "").split("\n") if ln.strip()]
    name = (conf_name or "").lower()
    for i in range(0, len(lines) - 1, 2):
        if lines[i].lower() == name:
            return lines[i + 1]
    if len(lines) >= 2:
        return lines[1]
    return ""


def policies_equal(left: str, right: str) -> bool:
    return (left or "").strip().lower() == (right or "").strip().lower()


def get_maxmemory_policies(
    addrs: List[str],
    password: str,
    bk_cloud_id: int,
    redis_rpc: Callable,
) -> Tuple[Dict[str, str], List[str]]:
    """confxx get maxmemory-policy，返回 addr -> policy 与错误列表"""
    policies: Dict[str, str] = {}
    errors: List[str] = []
    if not addrs:
        return policies, errors

    resp = redis_rpc(
        {
            "addresses": addrs,
            "db_num": 0,
            "password": password,
            "command": "confxx get {}".format(MAXMEMORY_POLICY),
            "bk_cloud_id": bk_cloud_id,
        }
    )
    for item in resp or []:
        addr = item.get("address") or ""
        if item.get("error_msg"):
            errors.append("{}: get {}: {}".format(addr, MAXMEMORY_POLICY, item["error_msg"]))
            continue
        policy = parse_confxx_get_value(item.get("result") or "", MAXMEMORY_POLICY)
        if not policy:
            errors.append("{}: get {} empty result".format(addr, MAXMEMORY_POLICY))
            continue
        policies[addr] = policy
    missing = [addr for addr in addrs if addr not in policies]
    if missing and not errors:
        errors.append("get {} no response: {}".format(MAXMEMORY_POLICY, missing))
    return policies, errors


def restore_maxmemory_policies(
    addr_policies: Dict[str, str],
    password: str,
    bk_cloud_id: int,
    redis_rpc: Callable,
) -> List[str]:
    """把每个实例的 maxmemory-policy 改回记录值，当前值已一致则跳过"""
    errors: List[str] = []
    if not addr_policies:
        return errors

    current_policies, errors = get_maxmemory_policies(
        addrs=list(addr_policies.keys()), password=password, bk_cloud_id=bk_cloud_id, redis_rpc=redis_rpc
    )
    for addr, expected_policy in addr_policies.items():
        current = current_policies.get(addr)
        if current is None or policies_equal(current, expected_policy):
            continue
        set_resp = redis_rpc(
            {
                "addresses": [addr],
                "db_num": 0,
                "password": password,
                "command": "confxx set {} {}".format(MAXMEMORY_POLICY, expected_policy),
                "bk_cloud_id": bk_cloud_id,
            }
        )
        set_item = (set_resp or [{}])[0]
        if set_item.get("error_msg"):
            errors.append("{}: set {} {}: {}".format(addr, MAXMEMORY_POLICY, expected_policy, set_item["error_msg"]))
            continue
        result = (set_item.get("result") or "").strip()
        if result and result.upper() != "OK":
            errors.append(
                "{}: set {} {} unexpected result: {}".format(addr, MAXMEMORY_POLICY, expected_policy, result)
            )
    return errors


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
    """内存分析前记录各实例当前的 maxmemory-policy"""

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


class RedisKeystatRestorePolicyService(BaseService):
    """内存分析后把 maxmemory-policy 改回分析前记录的值"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = _get_trans_data(data, kwargs)
        origin_policies = getattr(trans_data, "keystat_origin_maxmemory_policies", None) or {}

        errors: List[str] = []
        for cluster, addrs, password, cluster_errors in _iter_cluster_addrs(kwargs.get("infos") or []):
            if cluster_errors:
                errors.extend(cluster_errors)
                continue
            addr_policies = {addr: origin_policies[addr] for addr in addrs if origin_policies.get(addr)}
            missing = [addr for addr in addrs if addr not in addr_policies]
            if missing:
                errors.append("{}: no recorded {}: {}".format(cluster.immute_domain, MAXMEMORY_POLICY, missing))
            self.log_info(
                _("恢复 maxmemory-policy, cluster:{}, policies:{}").format(cluster.immute_domain, addr_policies)
            )
            errors.extend(
                restore_maxmemory_policies(
                    addr_policies=addr_policies,
                    password=password,
                    bk_cloud_id=cluster.bk_cloud_id,
                    redis_rpc=DRSApi.redis_rpc,
                )
            )
        if errors:
            for msg in errors:
                self.log_error(msg)
            return False
        self.log_info(_("maxmemory-policy 已恢复为分析前的值"))
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


class RedisKeystatRestorePolicyComponent(Component):
    name = __name__
    code = "redis_keystat_restore_policy"
    bound_service = RedisKeystatRestorePolicyService
