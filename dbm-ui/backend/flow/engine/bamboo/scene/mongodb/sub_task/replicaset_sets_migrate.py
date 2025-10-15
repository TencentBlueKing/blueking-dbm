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
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import install_plugin
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import add_install_dbmon
from backend.flow.engine.bamboo.scene.mongodb.sub_task.multi_instance_deinstall import multi_instance_deinstall
from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_migrate import replicaset_migrate
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def replicaset_set_migrate(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, replicaset_set_info: dict
) -> SubBuilder:
    """
    replicaset组迁移流程
    replicaset_set_info 表示replicaset组信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    if sub_get_kwargs.payload.get("cluster_type") != ClusterType.MongoShardedCluster.value:
        # 获取主机 包含老机器
        new_hosts = sub_get_kwargs.get_host_migrate(info=replicaset_set_info)

        # 安装蓝鲸插件
        sub_get_kwargs.payload["hosts"] = new_hosts
        sub_get_kwargs.payload["plugin_hosts"] = new_hosts
        install_plugin(pipeline=sub_pipeline, get_kwargs=sub_get_kwargs, new_cluster=False)

        # 介质下发
        sub_get_kwargs.payload["db_version"] = replicaset_set_info["db_version"]
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

    # 根据计算容量新的 cachesize 和 oplogsize  self.replicaset_info["cacheSizeGB"]  self.replicaset_info["oplogSizeMB"]
    if sub_get_kwargs.payload.get("cluster_type") == ClusterType.MongoShardedCluster.value:
        instance_num = len(replicaset_set_info["shard_set"])
    else:
        instance_num = len(replicaset_set_info["cluster_ids"])
    sub_get_kwargs.calc_param_migrate(info=replicaset_set_info["mongodb"][0], instance_num=instance_num)

    # 副本集进行替换 并行
    sub_sub_pipelines = []
    if replicaset_set_info.get("cluster_ids"):
        for cluster_id in replicaset_set_info["cluster_ids"]:
            sub_sub_pipeline = replicaset_migrate(
                root_id=root_id,
                ticket_data=ticket_data,
                sub_kwargs=sub_get_kwargs,
                cluster_id=cluster_id,
                shard_name="",
                replicaset_set_info=replicaset_set_info,
            )
            sub_sub_pipelines.append(sub_sub_pipeline)
    elif replicaset_set_info.get("shard_set"):
        for shard in replicaset_set_info["shard_set"]:
            sub_sub_pipeline = replicaset_migrate(
                root_id=root_id,
                ticket_data=ticket_data,
                sub_kwargs=sub_get_kwargs,
                cluster_id=0,
                shard_name=shard,
                replicaset_set_info=replicaset_set_info,
            )
            sub_sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_sub_pipelines)

    # 安装监控
    ip_list = replicaset_set_info["mongodb"]
    exec_ips = [host["ip"] for host in replicaset_set_info["mongodb"]]
    bk_cloud_id = ip_list[0]["bk_cloud_id"]
    add_install_dbmon(root_id, ticket_data, sub_pipeline, exec_ips, bk_cloud_id, allow_empty_instance=True)

    # 副本集组下架
    if sub_get_kwargs.payload.get("cluster_type") != ClusterType.MongoShardedCluster.value:
        sub_sub_pipeline = multi_instance_deinstall(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            info=replicaset_set_info,
        )
        sub_pipeline.add_sub_pipeline(sub_flow=sub_sub_pipeline)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--副本集组迁移"))
