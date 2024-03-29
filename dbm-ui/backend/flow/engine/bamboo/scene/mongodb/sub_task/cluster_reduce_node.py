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

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

from .replicaset_reduce_node import replicaset_reduce_node


def cluster_reduce_node(root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict) -> SubBuilder:
    """
    cluster减少节点流程
    info 表示同机器多cluster信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 设置变量
    sub_get_kwargs.payload["app"] = sub_get_kwargs.payload["bk_app_abbr"]
    sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoShardedCluster.value

    # 获取集群信息并计算对应关系
    sub_get_kwargs.calc_reduce_node(info=info)

    # 介质下发
    kwargs = sub_get_kwargs.get_send_media_kwargs(media_type="actuator")
    sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 创建原子任务执行目录
    kwargs = sub_get_kwargs.get_create_dir_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 获取mongos信息
    mongos_host = sub_get_kwargs.payload["mongos_nodes"][0]
    sub_get_kwargs.payload["nodes"] = [
        {"ip": mongos_host["ip"], "port": mongos_host["port"], "bk_cloud_id": mongos_host["bk_cloud_id"]}
    ]

    # 获取密码
    get_password = {}
    get_password["usernames"] = sub_get_kwargs.manager_users
    sub_get_kwargs.payload["passwords"] = sub_get_kwargs.get_password_from_db(info=get_password)["passwords"]

    # shard进行减少node——子流程并行
    sub_pipelines = []
    for db_instances in sub_get_kwargs.payload["shards_instance_relationships"].values():
        sub_get_kwargs.payload["db_instances"] = db_instances
        sub_sub_pipeline = replicaset_reduce_node(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            info={},
            cluster=True,
        )
        sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--{}增加节点".format(sub_get_kwargs.payload["cluster_name"])))
