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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.consts import MongoDBInstanceType, MongoInstanceDbmonType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.fast_exec_script import MongoFastExecScriptComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def multi_instance_deinstall(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict
) -> SubBuilder:
    """
    多个instance deinstall流程 放在流程最后
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 下架计算
    old_hosts, old_instances = sub_get_kwargs.get_old_host_migrate(info=info)

    # 介质下发
    sub_get_kwargs.payload["hosts"] = old_hosts
    kwargs = sub_get_kwargs.get_send_media_kwargs(media_type="actuator")
    sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 创建原子任务执行目录
    kwargs = sub_get_kwargs.get_create_dir_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 默认强制下架实例
    force = True

    acts_dbmon_list = []
    acts_instance_deinstall_list = []
    instance_type = MongoDBInstanceType.MongoD.value
    for instance in old_instances:
        # 删除dbmon
        sub_get_kwargs.payload["bk_cloud_id"] = instance["bk_cloud_id"]
        kwargs_delete_dbmon = sub_get_kwargs.get_dbmon_operation_kwargs(
            node_info=instance, operation_type=MongoInstanceDbmonType.DeleteDbmon
        )
        acts_dbmon_list.append(
            {
                "act_name": _("MongoDB-{}:{}-删除dbmon".format(instance["ip"], str(instance["port"]))),
                "act_component_code": MongoFastExecScriptComponent.code,
                "kwargs": kwargs_delete_dbmon,
            }
        )
        # 关闭实例
        sub_get_kwargs.payload["set_id"] = instance["set_id"]
        kwargs = sub_get_kwargs.get_mongo_deinstall_kwargs(
            node_info=instance, nodes_info=[instance], instance_type=instance_type, force=force, rename_dir=True
        )
        acts_instance_deinstall_list.append(
            {
                "act_name": _("MongoDB-{}:{}-{}卸载".format(instance["ip"], str(instance["port"]), instance_type)),
                "act_component_code": ExecuteDBActuatorJobComponent.code,
                "kwargs": kwargs,
            }
        )
    if acts_dbmon_list and acts_instance_deinstall_list:
        sub_pipeline.add_parallel_acts(acts_list=acts_dbmon_list)
        sub_pipeline.add_parallel_acts(acts_list=acts_instance_deinstall_list)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--多实例下架"))
