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
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, ClusterType, MachineType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    DeployPeripheralToolsDepart,
    remove_depart,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def prepare_departs_binary(
    root_id: str,
    data: Dict,
    cluster_type: ClusterType,
    departs: List[DeployPeripheralToolsDepart],
    proxy_cloud_ip_list: Dict[int, List[str]],
    storage_cloud_ip_list: Dict[int, List[str]],
) -> SubProcess:
    """
    {
      0: [1.1.1.1, 2.2.2.2], 云区域对应 ip
      1: [11.11.11]
    }
    """
    sp = SubBuilder(root_id=root_id, data=data)

    # 周边工具下发放在这里可以增加这个 subflow 的独立性
    acts = []
    for bk_cloud_id, ips in {
        k: proxy_cloud_ip_list[k] + storage_cloud_ip_list[k]
        for k in set(list(proxy_cloud_ip_list.keys()) + list(storage_cloud_ip_list.keys()))
    }.items():
        if len(ips) > 0:
            acts.append(
                {
                    "act_name": _("cloud_{} 下发 MySQL 周边程序介质".format(bk_cloud_id)),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=ips,
                            file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
                        )
                    ),
                }
            )

    sp.add_parallel_acts(acts_list=acts)

    acts = make_prepare_departs_binary_acts(
        machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.STORAGE],
        departs=departs,
        cloud_ip_list=storage_cloud_ip_list,
    )

    if cluster_type != ClusterType.TenDBSingle:
        departs_on_proxy = deepcopy(departs)
        remove_depart(DeployPeripheralToolsDepart.MySQLTableChecksum, departs_on_proxy)

        if cluster_type == ClusterType.TenDBHA:
            remove_depart(DeployPeripheralToolsDepart.MySQLRotateBinlog, departs_on_proxy)
            remove_depart(DeployPeripheralToolsDepart.MySQLDBBackup, departs_on_proxy)

        acts.extend(
            make_prepare_departs_binary_acts(
                machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.PROXY],
                departs=departs_on_proxy,
                cloud_ip_list=proxy_cloud_ip_list,
            )
        )

    sp.add_parallel_acts(acts_list=acts)
    return sp.build_sub_process(sub_name=_("准备周边组件二进制"))


def make_prepare_departs_binary_acts(
    machine_type: MachineType, departs: List[DeployPeripheralToolsDepart], cloud_ip_list
) -> List[Dict]:
    acts = []
    for bk_cloud_id, ip_list in cloud_ip_list.items():
        # for ip in ip_list:
        if len(ip_list) > 0:
            acts.append(
                {
                    "act_name": _("cloud_{} {} 部署二进制".format(bk_cloud_id, machine_type.value)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            exec_ip=ip_list,
                            run_as_system_user=DBA_ROOT_USER,
                            get_mysql_payload_func=MysqlActPayload.prepare_peripheraltools_binary.__name__,
                            cluster={"departs": departs, "machine_type": machine_type},
                            bk_cloud_id=bk_cloud_id,
                        )
                    ),
                }
            )

    return acts
