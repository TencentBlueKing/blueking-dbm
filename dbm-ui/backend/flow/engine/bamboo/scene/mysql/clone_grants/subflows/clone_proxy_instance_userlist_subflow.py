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
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, List, Tuple

from django.utils.translation import ugettext as _

from backend.db_meta.enums import MachineType
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.mysql.clone_grants.exceptions import MySQLCloneGrantsValidateException
from backend.flow.engine.bamboo.scene.mysql.clone_grants.subflows.helpers import __build_trans_actuator_acts
from backend.flow.engine.bamboo.scene.mysql.clone_grants.validator.clone_mysql_grants_flow_validator import (
    CloneMySQLGrantsFlowValidator,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def clone_proxy_instance_userlist_subflow(
    root_id: str,
    data: Dict,
    infos: List,
    with_actuator: bool,
) -> SubProcess:
    if not data.get("validated", False):
        v = CloneMySQLGrantsFlowValidator(ticket_data=data)
        if v:
            raise MySQLCloneGrantsValidateException(msg=v)

    cloud_ip_map, aggregated_infos = __aggregate_infos(infos)

    pipe = SubBuilder(root_id=root_id, data=data)

    if with_actuator:
        pipe.add_parallel_acts(acts_list=__build_trans_actuator_acts(cloud_ip_map=cloud_ip_map))

    clone_acts = []
    for info in aggregated_infos:
        bk_cloud_id = int(info["bk_cloud_id"])
        source_address = info["source_address"]
        dest_addresses = info["dest_addresses"]
        source_ip, source_port = source_address.split(":")

        clone_acts.append(
            {
                "act_name": _("克隆 {} 白名单".format(source_address)),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        exec_ip=source_ip,
                        get_mysql_payload_func=MysqlActPayload.get_clone_proxy_user_payload.__name__,
                        cluster={"source_address": source_address, "dest_addresses": dest_addresses},
                    )
                ),
            },
        )

    pipe.add_parallel_acts(acts_list=clone_acts)

    return pipe.build_sub_process(sub_name=_("白名单克隆"))


def __aggregate_infos(infos: List) -> Tuple[Dict, List]:
    """
    白名单克隆的 actuator 是在 source 上执行的
    所以 cloud_ip_map 只需要聚合 source ip
    """
    cloud_ip_map = defaultdict(set)
    aggregated_infos_dict = defaultdict(set)

    for info in infos:
        bk_cloud_id = int(info["bk_cloud_id"])
        source_address = info["source_address"]
        dest_addresses = info["dest_addresses"]

        k = f"{bk_cloud_id}-{source_address}"
        aggregated_infos_dict[k].update(dest_addresses)

        cloud_ip_map[bk_cloud_id].add(source_address.split(":")[0])

    aggregated_infos = []
    for k, v in aggregated_infos_dict.items():
        bk_cloud_id, source_address = k.split("-")
        aggregated_infos.append(
            {
                "bk_cloud_id": int(bk_cloud_id),
                "machine_type": MachineType.PROXY.value,
                "source_address": source_address,
                "dest_addresses": list(v),
            }
        )

    return cloud_ip_map, aggregated_infos
