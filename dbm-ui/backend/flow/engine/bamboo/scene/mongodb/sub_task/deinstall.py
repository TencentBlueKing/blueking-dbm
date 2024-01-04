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
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.delete_domain_from_dns import (
    ExecDeleteDomainFromDnsOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_password_from_db import (
    ExecDeletePasswordFromDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def mongo_deinstall_parallel(sub_get_kwargs: ActKwargs, nodes: list, instance_type: str) -> list:
    acts_list = []
    for node in nodes:
        kwargs = sub_get_kwargs.get_mongo_deinstall_kwargs(
            node_info=node, nodes_info=nodes, instance_type=instance_type
        )
        acts_list.append(
            {
                "act_name": _("MongoDB-{}-{}卸载".format(node["ip"], instance_type)),
                "act_component_code": ExecuteDBActuatorJobComponent.code,
                "kwargs": kwargs,
            }
        )
    return acts_list


def deinstall(root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, cluster_id: int) -> SubBuilder:
    """
    单个cluster卸载流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)
    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取单个cluster信息
    sub_get_kwargs.get_cluster_info_deinstall(cluster_id=cluster_id)

    # mongo卸载
    # 复制集卸载
    if sub_get_kwargs.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
        # mongo卸载——并行
        acts_list = mongo_deinstall_parallel(
            sub_get_kwargs=sub_get_kwargs, nodes=sub_get_kwargs.payload["nodes"], instance_type=MediumEnum.MongoD
        )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)
    # cluster卸载
    elif sub_get_kwargs.payload["cluster_type"] == ClusterType.MongoShardedCluster.value:
        # mongos卸载——并行
        acts_list = mongo_deinstall_parallel(
            sub_get_kwargs=sub_get_kwargs,
            nodes=sub_get_kwargs.payload["mongos_nodes"],
            instance_type=MediumEnum.MongoS,
        )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)
        # shard卸载——并行
        many_acts_list = []
        for shard_nodes in sub_get_kwargs.payload["shards_nodes"]:
            acts_list = mongo_deinstall_parallel(
                sub_get_kwargs=sub_get_kwargs, nodes=shard_nodes["nodes"], instance_type=MediumEnum.MongoD
            )
            many_acts_list.extend(acts_list)
        sub_pipeline.add_parallel_acts(acts_list=many_acts_list)
        # config卸载——并行
        acts_list = mongo_deinstall_parallel(
            sub_get_kwargs=sub_get_kwargs,
            nodes=sub_get_kwargs.payload["config_nodes"],
            instance_type=MediumEnum.MongoD,
        )
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

    # 删除dns
    kwargs = sub_get_kwargs.get_delete_domain_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-删除域名"),
        act_component_code=ExecDeleteDomainFromDnsOperationComponent.code,
        kwargs=kwargs,
    )

    # 删除保存在密码服务的密码
    kwargs = sub_get_kwargs.get_delete_pwd_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-删除密码"),
        act_component_code=ExecDeletePasswordFromDBOperationComponent.code,
        kwargs=kwargs,
    )

    # 删除db_meta关系
    kwargs = {"cluster_id": cluster_id}
    sub_pipeline.add_act(
        act_name=_("MongoDB-删除db_meta关系"),
        act_component_code=ExecDeletePasswordFromDBOperationComponent.code,
        kwargs=kwargs,
    )

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--卸载--cluster_id:{}".format(str(cluster_id))))
