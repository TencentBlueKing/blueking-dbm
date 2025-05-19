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
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from deprecated import deprecated
from django.utils.translation import ugettext as _

from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, ClusterType, MachineType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.clusters_detail_helper import (
    clusters_detail_ip_ports_by_access_layer,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


@deprecated
def instance_standardize(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    cluster_type: ClusterType,
    cluster_details: Dict[str, Dict[str, List[str]]],
) -> SubProcess:
    acts = []

    proxy_ip_port_dict, storage_ip_port_dict = clusters_detail_ip_ports_by_access_layer(cluster_details)

    if storage_ip_port_dict:
        acts = make_mysql_standardize_acts(
            bk_cloud_id=bk_cloud_id,
            ip_port_dict=storage_ip_port_dict,
            machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.STORAGE],
        )

    if proxy_ip_port_dict:
        if cluster_type == ClusterType.TenDBCluster:
            acts.extend(
                make_mysql_standardize_acts(
                    bk_cloud_id=bk_cloud_id, ip_port_dict=proxy_ip_port_dict, machine_type=MachineType.SPIDER
                )
            )
        elif cluster_type == ClusterType.TenDBHA:
            acts.extend(make_proxy_standardize_acts(bk_cloud_id=bk_cloud_id, ip_port_dict=proxy_ip_port_dict))

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_acts(acts_list=acts)
    return sp.build_sub_process(sub_name=_("实例标准化"))


def make_proxy_standardize_acts(bk_cloud_id: int, ip_port_dict) -> List:
    acts = []
    for ip, port_list in ip_port_dict.items():
        acts.append(
            {
                "act_name": _(f"{ip}:{port_list}"),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        run_as_system_user=DBA_ROOT_USER,
                        get_mysql_payload_func=MysqlActPayload.standardize_proxy.__name__,
                        cluster={"port_list": port_list},
                        bk_cloud_id=bk_cloud_id,
                    )
                ),
            }
        )
    return acts


@deprecated
def make_mysql_standardize_acts(bk_cloud_id: int, ip_port_dict, machine_type: MachineType) -> List:
    acts = []
    for ip, port_list in ip_port_dict.items():
        acts.append(
            {
                "act_name": _(f"{ip}:{port_list}"),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        run_as_system_user=DBA_ROOT_USER,
                        get_mysql_payload_func=MysqlActPayload.standardize_mysql.__name__,
                        cluster={"port_list": port_list, "machine_type": machine_type},
                        bk_cloud_id=bk_cloud_id,
                    )
                ),
            }
        )
    return acts


def standardize_instance(root_id: str, data: Dict, bk_cloud_id: int, instances: List[str]) -> SubProcess:
    ip_port_dict = defaultdict(list)
    for ins in instances:
        ip, port = ins.split(":")
        ip_port_dict[ip].append(int(port))

    acts = []
    for ip, ports in ip_port_dict.items():
        acts.append(
            {
                "act_name": "{}:{}".format(ip, ports),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=[ip],
                        run_as_system_user=DBA_ROOT_USER,
                        payload_class=PeripheralToolsPayload.payload_class_path(),
                        get_mysql_payload_func=PeripheralToolsPayload.standardize_instance.__name__,
                        bk_cloud_id=bk_cloud_id,
                        cluster={"ports": ports},
                    )
                ),
            }
        )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_acts(acts_list=acts)
    return sp.build_sub_process(sub_name=_("实例标准化"))
