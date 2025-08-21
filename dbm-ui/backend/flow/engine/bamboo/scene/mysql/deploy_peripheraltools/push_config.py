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
from dataclasses import asdict
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs

logger = logging.getLogger("flow")


def gen_reload_departs_config(
    root_id: str, data: Dict, bk_cloud_id: int, instances: List[str], departs: List[DeployPeripheralToolsDepart]
) -> SubProcess:
    ip_ports_dict = defaultdict(list)
    for inst in instances:
        ip, port = inst.split(":")
        ip_ports_dict[ip].append(int(port))

    ipsubs = []
    for ip, ports in ip_ports_dict.items():
        ipsub = SubBuilder(root_id=root_id, data=data)
        ipsub.add_act(
            act_name=_("生成配置: {}".format([d.value for d in departs])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=[ip],
                    run_as_system_user=DBA_ROOT_USER,
                    payload_class=PeripheralToolsPayload.payload_class_path(),
                    get_mysql_payload_func=PeripheralToolsPayload.gen_config.__name__,
                    bk_cloud_id=bk_cloud_id,
                    cluster={"ports": ports, "departs": departs},
                )
            ),
        )
        ipsub.add_act(
            act_name=_("重载配置: {}".format([d.value for d in departs])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=[ip],
                    bk_cloud_id=bk_cloud_id,
                    run_as_system_user=DBA_ROOT_USER,
                    payload_class=PeripheralToolsPayload.payload_class_path(),
                    get_mysql_payload_func=PeripheralToolsPayload.reload_config.__name__,
                    cluster={"ports": ports, "departs": departs},
                )
            ),
        )

        ipsubs.append(ipsub.build_sub_process(sub_name="{}:{}".format(ip, ports)))

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_sub_pipeline(sub_flow_list=ipsubs)
    return sp.build_sub_process(sub_name=_("推送加载 {} 配置".format(departs)))
