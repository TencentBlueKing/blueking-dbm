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
from backend.flow.engine.bamboo.scene.mongodb.sub_task.migrate_mongod_replace import migrate_mongod_replace
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def replicaset_migrate(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_kwargs: ActKwargs,
    cluster_id: int,
    shard_name: str,
    replicaset_set_info: dict,
) -> SubBuilder:
    """
    replicaset迁移流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取集群信息
    if cluster_id:
        sub_get_kwargs.get_cluster_info_deinstall(cluster_id=cluster_id)

    # 计算对应关系
    instance_relationships = sub_get_kwargs.get_instance_migrate_calc(
        info=replicaset_set_info,
        cluster_id=cluster_id,
        shard_name=shard_name,
    )

    # 获取node 的 role backup在最前面 primary在最后
    instance_relationships_node_role = sub_get_kwargs.get_role_kwargs(instance_relationships=instance_relationships)

    # 节点替换
    # 复制集进行替换——串行
    for instance_relationship in instance_relationships_node_role:
        sub_get_kwargs.db_instance = instance_relationship["instances"][0]
        sub_sub_pipeline = migrate_mongod_replace(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_sub_kwargs=sub_get_kwargs,
            cluster_role=sub_get_kwargs.db_instance.get("cluster_role"),
            info=instance_relationship,
        )
        sub_pipeline.add_sub_pipeline(sub_sub_pipeline)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--副本集迁移"))
