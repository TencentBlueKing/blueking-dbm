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
from typing import List

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import SqlserverVersion
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.validate import Host, SqlserverCluster


def install_sqlserver_sub_flow(
    uid: str,
    root_id: str,
    bk_biz_id: int,
    db_module_id: int,
    install_ports: list,
    clusters: List[SqlserverCluster],
    cluster_type: ClusterType,
    target_hosts: List[Host],
    db_version: SqlserverVersion,
):
    """
    拼接安装Sqlserver的子流程，以机器维度安装
    @param uid: 单据id
    @param root_id: 主流程的id
    @param bk_biz_id: 对应的业务id
    @param db_module_id: 对应的db模块id
    @param install_ports: 机器部署的端口列表，多实例场景
    @param clusters: 机器部署所关联的集群列表，多实例场景
    @param cluster_type: 集群类型
    @param target_hosts: 部署新机器列表
    @param db_version: 部署版本
    """
    # 构造只读上下文
    global_data = {
        "uid": uid,
        "bk_biz_id": bk_biz_id,
        "db_module_id": db_module_id,
        "install_ports": install_ports,
        "clusters": [asdict(i) for i in clusters],
        "cluster_type": cluster_type,
    }
    # 声明子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=global_data)

    sub_pipeline.add_act(
        act_name=_("下发安装包介质"),
        act_component_code=TransFileInWindowsComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                target_hosts=target_hosts,
                file_list=GetFileList(db_type=DBType.Sqlserver).get_sqlserver_package(db_version=db_version),
            ),
        ),
    )

    sub_pipeline.add_act(
        act_name=_("机器初始化"),
        act_component_code=SqlserverActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                exec_ips=target_hosts, get_payload_func=SqlserverActPayload.system_init_payload.__name__
            ),
        ),
    )

    acts_list = []
    for hosts in target_hosts:
        acts_list.append(
            {
                "act_name": _("安装Sqlserver实例:{}".format(hosts.ip)),
                "act_component_code": SqlserverActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ips=[hosts], get_payload_func=SqlserverActPayload.get_install_sqlserver_payload.__name__
                    ),
                ),
            }
        )
    sub_pipeline.add_parallel_acts(acts_list=acts_list)

    return sub_pipeline.build_sub_process(sub_name=_("安装sqlserver实例"))
