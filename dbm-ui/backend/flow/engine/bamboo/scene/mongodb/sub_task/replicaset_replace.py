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
from backend.flow.plugins.components.collections.mongodb.mongodb_cmr_4_meta import CMRMongoDBMetaComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

from .mongod_replace import mongod_replace


def replicaset_replace(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict, cluster_role: str
) -> SubBuilder:
    """
    replicaset 替换流程
    info 表示replicaset信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    if not cluster_role:
        # 获取信息
        sub_get_kwargs.get_host_replace(mongodb_type=ClusterType.MongoReplicaSet.value, info=info)

        # 介质下发
        kwargs = sub_get_kwargs.get_send_media_kwargs()
        sub_pipeline.add_act(
            act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
        )

    # 计算参数
    sub_get_kwargs.calc_param_replace(info=info)
    # 进行替换——并行 以ip为维度
    sub_sub_pipelines = []
    for mongodb_instance in info["instances"]:
        sub_get_kwargs.db_instance = mongodb_instance
        sub_sub_pipeline = mongod_replace(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_sub_kwargs=sub_get_kwargs,
            cluster_role=cluster_role,
            info=info,
        )
        sub_sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_sub_pipelines)

    # 修改db_meta数据
    info["created_by"] = sub_get_kwargs.payload.get("created_by")
    info["bk_biz_id"] = sub_get_kwargs.payload.get("bk_biz_id")
    if not cluster_role:
        info["db_type"] = "replicaset_mongodb"
        name = "replicaset"
        for mongodb_instance in info["instances"]:
            kwargs = sub_get_kwargs.get_change_meta_replace_kwargs(info=info, instance=mongodb_instance)
            sub_pipeline.add_act(
                act_name=_("MongoDB-mongod修改meta-port:{}".format(str(mongodb_instance["port"]))),
                act_component_code=CMRMongoDBMetaComponent.code,
                kwargs=kwargs,
            )
    else:
        if cluster_role == MongoDBClusterRole.ShardSvr.value:
            info["db_type"] = "cluster_mongodb"
            name = "shard"

        elif cluster_role == MongoDBClusterRole.ConfigSvr.value:
            info["db_type"] = "mongo_config"
            name = "configDB"
        kwargs = sub_get_kwargs.get_change_meta_replace_kwargs(info=info, instance={})
        sub_pipeline.add_act(
            act_name=_("MongoDB-mongod修改meta"), act_component_code=CMRMongoDBMetaComponent.code, kwargs=kwargs
        )

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--{}整机替换--ip:{}".format(name, info["ip"])))
