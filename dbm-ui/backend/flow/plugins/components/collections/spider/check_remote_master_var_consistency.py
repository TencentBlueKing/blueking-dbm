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
from collections import defaultdict

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components.db_remote_service.client import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.remote_master_var_consistency import (
    ABSENT,
    CHECKED_VARS,
    KIND_ABSENT,
    InstanceVarMap,
    diff_remote_masters,
)

logger = logging.getLogger("flow")

DRS_ADDRESS_CHUNK_SIZE = 10
SHOW_REMOTE_MASTER_VARS_SQL = "SHOW GLOBAL VARIABLES WHERE Variable_name IN ({})".format(
    ", ".join("'{}'".format(var.name) for var in CHECKED_VARS)
)


def running_remote_masters(cluster):
    return list(
        cluster.storageinstance_set.filter(
            instance_role=InstanceRole.REMOTE_MASTER.value,
            status=InstanceStatus.RUNNING.value,
        )
        .select_related("machine")
        .order_by("machine__ip", "port")
    )


def query_remote_master_variables(instances):
    """返回成功取回的变量表，以及未送进比较的地址错误。"""
    by_address = {}
    grouped = defaultdict(list)
    for instance in instances:
        address = "{}{}{}".format(instance.machine.ip, IP_PORT_DIVIDER, instance.port)
        by_address[address] = instance
        grouped[instance.machine.bk_cloud_id].append(address)

    variables_by_address = {}
    errors_by_address = {}
    for bk_cloud_id, addresses in grouped.items():
        for start in range(0, len(addresses), DRS_ADDRESS_CHUNK_SIZE):
            _query_chunk(
                bk_cloud_id,
                addresses[start : start + DRS_ADDRESS_CHUNK_SIZE],
                variables_by_address,
                errors_by_address,
            )

    var_maps = []
    errors = []
    for address, instance in by_address.items():
        error = errors_by_address.get(address)
        variables = variables_by_address.get(address)
        if error is not None or variables is None:
            errors.append((instance.machine.ip, instance.port, error or _("DRS未返回该地址")))
            continue
        var_maps.append(InstanceVarMap(ip=instance.machine.ip, port=instance.port, variables=variables))
    return var_maps, errors


def format_query_errors(errors) -> str:
    lines = [_("查询主分片变量失败")]
    for ip, port, error in errors:
        lines.append("{}:{} {}".format(ip, port, error))
    return "\n".join(lines)


def format_mismatches(mismatches) -> str:
    lines = [_("主分片运行时变量不一致")]
    for mismatch in mismatches:
        kind_text = _("缺失") if mismatch.kind == KIND_ABSENT else _("值不同")
        lines.append(_("变量 {}，{}").format(mismatch.name, kind_text))
        for ip, port, raw in mismatch.rows:
            shown = _("缺失") if raw is ABSENT else raw
            lines.append("{}:{} {}".format(ip, port, shown))
    return "\n".join(lines)


def _query_chunk(bk_cloud_id, addresses, variables_by_address, errors_by_address):
    try:
        resp = DRSApi.rpc(
            {
                "addresses": addresses,
                "cmds": [SHOW_REMOTE_MASTER_VARS_SQL],
                "force": True,
                "bk_cloud_id": bk_cloud_id,
            }
        )
    except Exception as err:
        logger.error(
            _("批量查询主分片变量失败，云区域 {}，错误: {}").format(bk_cloud_id, str(err)),
            exc_info=True,
        )
        for address in addresses:
            errors_by_address[address] = str(err)
        return
    _apply_response(addresses, resp, variables_by_address, errors_by_address)


def _apply_response(addresses, resp, variables_by_address, errors_by_address):
    if not isinstance(resp, list) or not resp:
        message = _("DRS返回格式异常") if not isinstance(resp, list) else _("DRS返回为空值")
        for address in addresses:
            errors_by_address[address] = message
        return
    seen = set()
    for item in resp:
        address = item.get("address", "")
        seen.add(address)
        variables, error = _variables_from_item(item)
        if error is not None:
            errors_by_address[address] = error
            continue
        variables_by_address[address] = variables
    for address in addresses:
        if address not in seen and address not in errors_by_address:
            errors_by_address[address] = _("DRS未返回该地址")


def _variables_from_item(item):
    if not isinstance(item, dict):
        return None, _("DRS返回格式异常")
    if item.get("error_msg") or not item.get("cmd_results"):
        return None, item.get("error_msg") or _("DRS返回为空值")
    try:
        cmd_result = item["cmd_results"][0]
    except (KeyError, IndexError, TypeError):
        return None, _("DRS返回格式异常")
    if not isinstance(cmd_result, dict):
        return None, _("DRS返回格式异常")
    if cmd_result.get("error_msg"):
        return None, cmd_result.get("error_msg")
    table_data = cmd_result.get("table_data")
    if not table_data:
        return None, _("DRS返回为空值")
    variables = {}
    for row in table_data:
        if not isinstance(row, dict):
            continue
        name = row.get("Variable_name")
        if not name:
            continue
        value = row.get("Value")
        variables[str(name).lower()] = "" if value is None else str(value)
    if not variables:
        return None, _("DRS返回为空值")
    return variables, None


class CheckRemoteMasterVarConsistencyService(BaseService):
    """变更执行前检查 RUNNING remote_master 的运行时变量是否一致。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        instances = running_remote_masters(cluster)
        if not instances:
            self.log_error(_("没有 RUNNING 的 remote_master"))
            return False
        var_maps, errors = query_remote_master_variables(instances)
        failed = _log_query_errors(self, errors)
        failed = _log_mismatches(self, var_maps) or failed
        return not failed


def _log_query_errors(service, errors) -> bool:
    if not errors:
        return False
    service.log_error(format_query_errors(errors))
    return True


def _log_mismatches(service, var_maps) -> bool:
    if not var_maps:
        return False
    mismatches = diff_remote_masters(var_maps)
    if not mismatches:
        return False
    service.log_error(format_mismatches(mismatches))
    return True


class CheckRemoteMasterVarConsistencyComponent(Component):
    name = __name__
    code = "check_remote_master_var_consistency"
    bound_service = CheckRemoteMasterVarConsistencyService
