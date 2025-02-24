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
from dataclasses import asdict
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, ClusterType, MachineType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def instance_standardize(
    root_id: str, data: Dict, cluster_type: ClusterType, proxy_group, storage_group
) -> SubProcess:
    acts = make_mysql_standardize_acts(
        storage_group, machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.STORAGE]
    )

    if cluster_type == ClusterType.TenDBCluster:
        acts.extend(make_mysql_standardize_acts(ip_group=proxy_group, machine_type=MachineType.SPIDER))
    elif cluster_type == ClusterType.TenDBHA:
        acts.extend(make_proxy_standardize_acts(proxy_group))

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_acts(acts_list=acts)
    return sp.build_sub_process(sub_name=_("实例标准化"))


def make_proxy_standardize_acts(ip_group) -> List:
    acts = []
    for bk_cloud_id, ip_dicts in ip_group.items():
        for ip, port_list in ip_dicts.items():
            acts.append(
                {
                    "act_name": _(f"{ip}"),
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


def make_mysql_standardize_acts(ip_group, machine_type: MachineType) -> List:
    acts = []
    for bk_cloud_id, ip_group in ip_group.items():
        for ip, port_list in ip_group.items():
            acts.append(
                {
                    "act_name": _(f"{ip}"),
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
