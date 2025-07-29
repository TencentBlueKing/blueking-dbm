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
from dataclasses import asdict
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs

logger = logging.getLogger("flow")


def deploy_binary(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
    departs: List[DeployPeripheralToolsDepart],
) -> SubProcess:
    """
    把一个 ip 要部署哪些包放到了 payload 中决定
    所以每个 ip 的参数可能不一样
    只能按 ip 单个执行
    这不是执行效率最高的, 但是编码非常简单
    """
    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_act(
        act_name=_("下发二进制包"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=ips,
                file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
            )
        ),
    )

    acts = []
    for ip in ips:
        acts.append(
            {
                "act_name": _("部署二进制 {}".format(ip)),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=[ip],
                        run_as_system_user=DBA_ROOT_USER,
                        payload_class=PeripheralToolsPayload.payload_class_path(),
                        get_mysql_payload_func=PeripheralToolsPayload.deploy_binary.__name__,
                        bk_cloud_id=bk_cloud_id,
                        cluster={"departs": departs},
                    )
                ),
            }
        )

    sp.add_parallel_acts(acts)
    return sp.build_sub_process(sub_name=_("准备周边二进制"))
