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

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import install_plugin
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import add_install_dbmon
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

from .replicaset_set_increase_node_by_ip import replicaset_set_increase_node_by_ip


def replicaset_set_increase_node(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict
) -> SubBuilder:
    """
    同机器多replicaset增加节点流程
    info 表示同机器多replicaset信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 设置变量
    info["target"] = info["add_shard_nodes"][0]

    # 计算cacheSize oplogSize
    sub_get_kwargs.calc_param_replace(info=info, instance_num=len(info["cluster_ids"]))

    # 获取主机信息
    sub_get_kwargs.get_host_increase_node(info=info)

    # 安装蓝鲸插件
    install_plugin(pipeline=sub_pipeline, get_kwargs=sub_get_kwargs, new_cluster=False)

    # 介质下发
    kwargs = sub_get_kwargs.get_send_media_kwargs(media_type="all")
    sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 创建原子任务执行目录
    kwargs = sub_get_kwargs.get_create_dir_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 机器初始化
    kwargs = sub_get_kwargs.get_os_init_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-机器初始化"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 以IP为维度增加node——子流程并行
    sub_sub_pipelines = []
    for node_index, add_shard_node in enumerate(info["add_shard_nodes"]):
        # 机器的索引即是增加node的索引
        info["add_shard_node"] = add_shard_node
        info["add_shard_node"]["node_index"] = node_index
        sub_sub_pipeline = replicaset_set_increase_node_by_ip(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            info=info,
            cluster=False,
        )
        sub_sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_sub_pipelines)

    # 安装dbmon 副本集
    ip_list = sub_get_kwargs.payload["plugin_hosts"]
    exec_ips = [host["ip"] for host in ip_list]
    add_install_dbmon(
        root_id=root_id,
        flow_data=ticket_data,
        pipeline=sub_pipeline,
        iplist=exec_ips,
        bk_cloud_id=ip_list[0]["bk_cloud_id"],
        allow_empty_instance=True,
    )

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--{}增加node".format("replicaset")))
