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
import copy
from dataclasses import asdict

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.db_meta.models import StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_check_processlist import MySQLCheckProcesslistComponent
from backend.flow.utils.mysql.mysql_act_dataclass import CheckProcesslistKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def uninstall_instance_sub_flow(
    root_id: str, ticket_data: dict, ip: str, ports: list = None, need_check_client_connect=True, error_ignorable=False
):
    """
    卸载storage指定ip ports下的实例
    @param root_id: flow流程的 root_id
    @param ticket_data: 单据 data 对象
    @param ip: 指定卸载的ip
    @param ports: 指定卸载端口,None表示卸载该ip下所有实例
    """
    ticket_data["force"] = ticket_data.get("force", False)
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    conditions = Q(machine__ip=ip, machine__bk_cloud_id=ticket_data["bk_cloud_id"])
    if ports is not None:
        conditions &= Q(port__in=ports)
    storage_instances = StorageInstance.objects.filter(conditions).order_by("port")

    sub_pipeline_list = []
    for storage in storage_instances:
        uninstall_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
        if need_check_client_connect:
            uninstall_pipeline.add_act(
                act_name=_("检查实例链接{}").format(storage.ip_port),
                act_component_code=MySQLCheckProcesslistComponent.code,
                kwargs=asdict(
                    CheckProcesslistKwargs(
                        bk_cloud_id=ticket_data["bk_cloud_id"],
                        instance_ip=storage.machine.ip,
                        instance_port=storage.port,
                        only_show_processlist=True,
                    )
                ),
                error_ignorable=error_ignorable,
            )
        cluster = {"uninstall_ip": ip, "bk_cloud_id": ticket_data["bk_cloud_id"], "backend_port": storage.port}
        uninstall_pipeline.add_act(
            act_name=_("卸载实例 {}".format(storage.ip_port)),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=storage.machine.ip,
                    bk_cloud_id=cluster["bk_cloud_id"],
                    cluster=copy.deepcopy(cluster),
                    get_mysql_payload_func=MysqlActPayload.get_uninstall_mysql_payload.__name__,
                )
            ),
            error_ignorable=error_ignorable,
        )
        sub_pipeline_list.append(uninstall_pipeline.build_sub_process(sub_name=_(" {} 卸载实例".format(storage.ip_port))))
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
    return sub_pipeline.build_sub_process(sub_name=_(" {} 卸载实例".format(ip)))
