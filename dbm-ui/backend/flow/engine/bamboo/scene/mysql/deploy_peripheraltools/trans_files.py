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

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER, DEPENDENCIES_PLUGINS
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs, InstallNodemanPluginKwargs
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs


def trans_common_files(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    bk_biz_id: int,
    ips: List[str],
    with_backup_client: bool,
    with_actuator: bool,
    with_bk_plugin: bool,
) -> SubProcess:
    """
    下发公共文件
    1. actuator, 某些复用场景不需要下发
    2. 安装蓝鲸插件
    """
    acts = []
    if with_actuator:
        acts.append(
            {
                "act_name": _("下发 actuator"),
                "act_component_code": TransFileComponent.code,
                "kwargs": asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ips,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            },
        )

    # acts.append(
    #     {
    #         "act_name": _("初始化 nginx 地址"),
    #         "act_component_code": ExecuteDBActuatorScriptComponent.code,
    #         "kwargs": asdict(
    #             ExecActuatorKwargs(
    #                 bk_cloud_id=bk_cloud_id,
    #                 exec_ip=ips,
    #                 run_as_system_user=DBA_ROOT_USER,
    #                 payload_class=PeripheralToolsPayload.payload_class_path(),
    #                 get_mysql_payload_func=PeripheralToolsPayload.init_nginx_addresses.__name__,
    #             )
    #         )
    #     }
    # )

    if with_backup_client:
        acts.append(
            {
                "act_name": _("安装 backup client"),
                "act_component_code": DownloadBackupClientComponent.code,
                "kwargs": asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=bk_cloud_id,
                        bk_biz_id=bk_biz_id,
                        download_host_list=ips,
                    )
                ),
            }
        )

    if with_bk_plugin:
        for plugin_name in DEPENDENCIES_PLUGINS:
            acts.append(
                {
                    "act_name": _("安装 {}".format(plugin_name)),
                    "act_component_code": InstallNodemanPluginServiceComponent.code,
                    "kwargs": asdict(
                        InstallNodemanPluginKwargs(ips=ips, plugin_name=plugin_name, bk_cloud_id=bk_cloud_id)
                    ),
                }
            )

    sp = SubBuilder(root_id=root_id, data=data)
    sp.add_parallel_acts(acts_list=acts)

    sp.add_act(
        act_name=_("初始化 nginx 地址"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=ips,
                run_as_system_user=DBA_ROOT_USER,
                payload_class=PeripheralToolsPayload.payload_class_path(),
                get_mysql_payload_func=PeripheralToolsPayload.init_nginx_addresses.__name__,
            )
        ),
    )

    return sp.build_sub_process(sub_name=_("下发公共文件"))
