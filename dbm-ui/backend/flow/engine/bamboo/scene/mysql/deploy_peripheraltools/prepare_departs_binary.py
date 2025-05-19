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
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from deprecated import deprecated
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterMachineAccessTypeDefine, ClusterType, MachineType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.clusters_detail_helper import (
    clusters_detail_ips,
    clusters_detail_ips_by_access_layer,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    DeployPeripheralToolsDepart,
    remove_depart,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


@deprecated
def prepare_departs_binary(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    cluster_type: ClusterType,
    cluster_details: dict,
    departs: List[DeployPeripheralToolsDepart],
) -> SubProcess:
    """
    {
      0: [1.1.1.1, 2.2.2.2], 云区域对应 ip
      1: [11.11.11]
    }
    """
    sp = SubBuilder(root_id=root_id, data=data)

    # 这个肯定会执行
    sp.add_parallel_acts(
        acts_list=[
            {
                "act_name": _("cloud_{} 下发 MySQL 周边程序介质".format(bk_cloud_id)),
                "act_component_code": TransFileComponent.code,
                "kwargs": asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=clusters_detail_ips(cluster_details),
                        file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
                    )
                ),
            }
        ]
    )

    proxy_ips, storage_ips = clusters_detail_ips_by_access_layer(cluster_details)

    acts = []

    if storage_ips:
        acts.append(
            make_prepare_departs_binary_act(
                machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.STORAGE],
                departs=departs,
                bk_cloud_id=bk_cloud_id,
                ip_list=storage_ips,
            )
        )

    if cluster_type != ClusterType.TenDBSingle and proxy_ips:
        departs_on_proxy = deepcopy(departs)
        remove_depart(DeployPeripheralToolsDepart.MySQLTableChecksum, departs_on_proxy)
        remove_depart(DeployPeripheralToolsDepart.MySQLRotateBinlog, departs_on_proxy)
        remove_depart(DeployPeripheralToolsDepart.MySQLDBBackup, departs_on_proxy)

        logger.info("{} proxy push departs binary {}".format(cluster_type, departs_on_proxy))
        acts.append(
            make_prepare_departs_binary_act(
                machine_type=ClusterMachineAccessTypeDefine[cluster_type][AccessLayer.PROXY],
                departs=departs_on_proxy,
                bk_cloud_id=bk_cloud_id,
                ip_list=proxy_ips,
            )
        )

    if acts:
        sp.add_parallel_acts(acts_list=acts)

    return sp.build_sub_process(sub_name=_("准备周边组件二进制"))


@deprecated
def make_prepare_departs_binary_act(
    machine_type: MachineType, departs: List[DeployPeripheralToolsDepart], bk_cloud_id: int, ip_list: List[str]
) -> Dict:
    return {
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
                "act_name": "{}".format(ip),
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
