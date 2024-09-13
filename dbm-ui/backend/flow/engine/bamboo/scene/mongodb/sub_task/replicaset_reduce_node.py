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

from .reduce_mongod import reduce_mongod


def replicaset_reduce_node(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict, cluster: bool
) -> SubBuilder:
    """
    replicaset减少节点流程
    info 表示replicaset信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    if not cluster:
        # 设置变量
        sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoReplicaSet.value

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

    # 复制集进行减少node——子流程串行
    sub_pipelines = []
    for db_instance in sub_get_kwargs.payload["db_instances"]:
        sub_get_kwargs.db_instance = db_instance
        sub_sub_pipeline = reduce_mongod(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            cluster=cluster,
        )
        sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--{}减少节点".format("replicaset")))
