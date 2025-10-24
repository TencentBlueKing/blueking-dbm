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

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import install_plugin
from backend.flow.engine.bamboo.scene.mongodb.sub_task.multi_instance_deinstall import multi_instance_deinstall
from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_sets_migrate import replicaset_set_migrate
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def cluster_migrate(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, cluster_info: dict
) -> SubBuilder:
    """
    cluster迁移流程
    cluster_info 表示集群信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取集群信息
    sub_get_kwargs.get_cluster_info_deinstall(cluster_id=cluster_info["cluster_id"])

    # 获取主机 包含老机器
    new_hosts = sub_get_kwargs.get_host_migrate(info=cluster_info)

    # 安装蓝鲸插件
    sub_get_kwargs.payload["hosts"] = new_hosts
    sub_get_kwargs.payload["plugin_hosts"] = new_hosts
    install_plugin(pipeline=sub_pipeline, get_kwargs=sub_get_kwargs, new_cluster=False)

    # 介质下发
    sub_get_kwargs.payload["db_version"] = cluster_info["db_version"]
    kwargs = sub_get_kwargs.get_send_media_kwargs(media_type="all")
    sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 创建原子任务执行目录
    kwargs = sub_get_kwargs.get_create_dir_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 新机器初始化
    kwargs = sub_get_kwargs.get_os_init_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-机器初始化"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 计算shard 组与机器对应关下
    cluster_shards_host_relationship = sub_get_kwargs.calc_cluster_shards_host(cluster_info=cluster_info)

    # shard 组进行替换 并行
    sub_sub_pipelines = []
    for shard_set in cluster_shards_host_relationship:
        sub_sub_pipeline = replicaset_set_migrate(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            replicaset_set_info=shard_set,
        )
        sub_sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_sub_pipelines)

    # 下架实例
    sub_sub_pipeline = multi_instance_deinstall(
        root_id=root_id,
        ticket_data=ticket_data,
        sub_kwargs=sub_get_kwargs,
        info=cluster_info,
    )
    sub_pipeline.add_sub_pipeline(sub_flow=sub_sub_pipeline)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--cluster迁移"))
