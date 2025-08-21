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
from django.utils.translation import ugettext as _

from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.plugins.components.collections.mysql.cluster_standardize_trans_module import (
    ClusterStandardizeTransModuleComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs


def cc_standardize(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    instances: List[str],
    with_cc_standardize: bool,
    with_exporter_config: bool,
) -> SubProcess:
    """
    生成 exporter 配置
    cc 模块移动
    """
    sub_flow_list = [
        gen_exporter_cnf(root_id=root_id, data=data, bk_cloud_id=bk_cloud_id, instances=instances),
    ]

    if with_cc_standardize and len(data.get("cluster_ids", [])) > 0:
        sub_flow_list.append(
            trans_cc_module(
                root_id=root_id, data=data, bk_cloud_id=bk_cloud_id, cluster_ids=data.get("cluster_ids", [])
            )
        )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_sub_pipeline(sub_flow_list=sub_flow_list)
    return sp.build_sub_process(sub_name=_("CC 标准化"))


def gen_exporter_cnf(root_id: str, data: Dict, bk_cloud_id: int, instances: List[str]) -> SubProcess:
    ip_port_dict = defaultdict(list)
    for ins in instances:
        ip, port = ins.split(":")
        ip_port_dict[ip].append(int(port))

    acts = []
    for ip, port_list in ip_port_dict.items():
        acts.append(
            {
                "act_name": _("{}:{}".format(ip, port_list)),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=[ip],
                        run_as_system_user=DBA_ROOT_USER,
                        payload_class=PeripheralToolsPayload.payload_class_path(),
                        get_mysql_payload_func=PeripheralToolsPayload.gen_config.__name__,
                        cluster={"ports": port_list, "departs": [DeployPeripheralToolsDepart.Exporter]},
                        bk_cloud_id=bk_cloud_id,
                    )
                ),
            }
        )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_acts(acts_list=acts)
    return sp.build_sub_process(sub_name=_("生成 exporter 配置"))


def trans_cc_module(root_id: str, data: Dict, bk_cloud_id: int, cluster_ids: List[int]) -> SubProcess:
    acts = []
    for cluster_id in cluster_ids:
        cluster_obj = Cluster.objects.get(pk=cluster_id)
        acts.append(
            {
                "act_name": _("CC 模块标准化: {}".format(cluster_obj.immute_domain)),
                "act_component_code": ClusterStandardizeTransModuleComponent.code,
                "kwargs": {"cluster_id": cluster_id},
            }
        )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_acts(acts_list=acts)
    return sp.build_sub_process(sub_name=_("CC 模块标准化"))
