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

from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, ClusterType
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.cluster_standardize_trans_module import (
    ClusterStandardizeTransModuleComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def cc_trans_module(
    root_id: str, data: Dict, cluster_type: ClusterType, cluster_objects: List[Cluster], proxy_group, storage_group
) -> SubProcess:
    """
    1. 按实例下发 exporter 配置
    2. cc 模块移动
    """
    sp = SubBuilder(root_id=root_id, data=data)

    sub_flow_list = [
        push_exporter_cnf(
            root_id=root_id,
            data=data,
            cloud_ip_group=storage_group,
            machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.STORAGE],
        )
    ]
    if cluster_type != ClusterType.TenDBSingle:
        sub_flow_list.append(
            push_exporter_cnf(
                root_id=root_id,
                data=data,
                cloud_ip_group=proxy_group,
                machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.PROXY],
            )
        )

    sp.add_parallel_sub_pipeline(sub_flow_list=sub_flow_list)

    acts = []
    for cluster_obj in cluster_objects:
        acts.append(
            {
                "act_name": _("{} CC 标准化".format(cluster_obj.immute_domain)),
                "act_component_code": ClusterStandardizeTransModuleComponent.code,
                "kwargs": {
                    "cluster_id": cluster_obj.id,
                },
            }
        )

    sp.add_parallel_acts(acts_list=acts)

    return sp.build_sub_process(sub_name=_("CC 标准化"))


def push_exporter_cnf(root_id: str, data: Dict, cloud_ip_group, machine_type):
    acts = []
    for bk_cloud_id, ip_dicts in cloud_ip_group.items():
        for ip, port_list in ip_dicts.items():
            acts.append(
                {
                    "act_name": _(f"{ip}:{port_list}"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            exec_ip=ip,
                            run_as_system_user=DBA_ROOT_USER,
                            get_mysql_payload_func=MysqlActPayload.push_exporter_cnf.__name__,
                            cluster={"port_list": port_list, "machine_type": machine_type},
                            bk_cloud_id=bk_cloud_id,
                        )
                    ),
                }
            )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_acts(acts_list=acts)
    return sp.build_sub_process(sub_name=_("{} 生成 exporter 配置".format(machine_type)))
