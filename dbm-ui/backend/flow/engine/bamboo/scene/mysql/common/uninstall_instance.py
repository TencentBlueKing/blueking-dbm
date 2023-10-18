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

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.spider.tendb_cluster_info import get_remotedb_info


def uninstall_instance_sub_flow(root_id: str, ticket_data: dict, ip: str, ports: list = None):
    """
    卸载remotedb 指定ip节点下的所有实例
    @param root_id: flow流程的root_id
    @param ticket_data: 单据 data 对象
    @param ip: 指定卸载的ip
    @param ports: 指定卸载端口,如果None,表明卸载该ip下所有实例
    """
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    cluster = {"uninstall_ip": ip, "bk_cloud_id": ticket_data["bk_cloud_id"]}
    instances = get_remotedb_info(cluster["uninstall_ip"], cluster["bk_cloud_id"])
    sub_pipeline_list = []
    for instance in instances:
        if ports is not None and instance["port"] not in ports:
            continue
        cluster["backend_port"] = instance["port"]
        sub_pipeline_list.append(
            {
                "act_name": _("卸载MySQL实例:{}:{}".format(cluster["uninstall_ip"], cluster["backend_port"])),
                "act_component_code": ExecuteDBActuatorScriptComponent.code,
                "kwargs": asdict(
                    ExecActuatorKwargs(
                        exec_ip=cluster["uninstall_ip"],
                        bk_cloud_id=cluster["bk_cloud_id"],
                        cluster=cluster,
                        get_mysql_payload_func=MysqlActPayload.get_uninstall_mysql_payload.__name__,
                    )
                ),
            }
        )
    sub_pipeline.add_parallel_acts(sub_pipeline_list)
    return sub_pipeline.build_sub_process(sub_name=_("Remote node {} 卸载整机实例".format(cluster["uninstall_ip"])))
