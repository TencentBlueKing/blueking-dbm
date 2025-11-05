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

from backend.flow.consts import MongoDBClusterRole
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import add_install_dbmon
from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_scale import replicaset_scale
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def cluster_host_set_scale(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_kwargs: ActKwargs,
    one_host_set_shards_instance_relationships: dict,
) -> SubBuilder:
    """
    机器组 容量变更流程
    info 表示机器组对应实例关系
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 进行shard——并行
    sub_sub_pipelines = []
    for shard_instance_relationships in one_host_set_shards_instance_relationships[
        "host_set_shards_instance_relationships"
    ]:
        sub_get_kwargs.payload["instance_relationships"] = shard_instance_relationships
        sub_sub_pipeline = replicaset_scale(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            info=shard_instance_relationships,
            cluster_role=MongoDBClusterRole.ShardSvr.value,
        )
        sub_sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_sub_pipelines)

    # 安装dbmon
    ip_list = one_host_set_shards_instance_relationships["new_hosts"]
    exec_ips = [host["ip"] for host in ip_list]
    add_install_dbmon(
        root_id=root_id,
        flow_data=ticket_data,
        pipeline=sub_pipeline,
        iplist=exec_ips,
        bk_cloud_id=ip_list[0]["bk_cloud_id"],
        allow_empty_instance=True,
    )

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--容量变更--机器组"))
