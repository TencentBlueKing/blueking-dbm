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
from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.mongodb_scale_repls_meta import MongoScaleReplsMetaComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

from .increase_mongod import increase_mongod


def replicaset_set_increase_node_by_ip(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict, cluster: bool
) -> SubBuilder:
    """
    同机器多replicaset增加节点流程
    info 表示同机器多replicaset信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取集群信息并计算对应关系
    if not cluster:
        sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoReplicaSet.value
        sub_get_kwargs.calc_increase_node(info=info)
        ip = info["add_shard_node"]["ip"]
        cluster_role = ""
    else:
        sub_get_kwargs.payload["replicaset_set"] = info
        ip = sub_get_kwargs.payload["add_shard_node"]
        cluster_role = MongoDBClusterRole.ShardSvr.value

    # 复制集维度增加node——子流程并行
    sub_sub_pipelines = []
    for replicaset in sub_get_kwargs.payload["replicaset_set"]:
        sub_get_kwargs.db_instance = replicaset
        sub_sub_pipeline = increase_mongod(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            info=replicaset,
            cluster_role=cluster_role,
        )
        sub_sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_sub_pipelines)

    # 修改meta——串行
    if not cluster:
        for scale_out in sub_get_kwargs.payload["scale_outs"]:
            kwargs = sub_get_kwargs.get_meta_scale_node_kwargs(info=[scale_out], increase=True)
            sub_pipeline.add_act(
                act_name=_("MongoDB-修改meta-{}:{}".format(scale_out["ip"], str(scale_out["port"]))),
                act_component_code=MongoScaleReplsMetaComponent.code,
                kwargs=kwargs,
            )

    else:
        kwargs = sub_get_kwargs.get_meta_scale_node_kwargs(
            info=sub_get_kwargs.payload["scale_out_instances_by_ip"][sub_get_kwargs.payload["add_shard_node"]],
            increase=True,
        )
        sub_pipeline.add_act(
            act_name=_("MongoDB-修改meta"),
            act_component_code=MongoScaleReplsMetaComponent.code,
            kwargs=kwargs,
        )

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--{}增加node".format(ip)))
