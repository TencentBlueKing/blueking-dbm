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
from backend.flow.consts import MongoDBClusterRole, MongoDBInstanceType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.mongodb_cmr_4_meta import CMRMongoDBMetaComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

from .mongos_replace import mongos_replace
from .replicaset_replace import replicaset_replace


def cluster_replace(root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict) -> SubBuilder:
    """
    cluster 替换流程
    info 表示cluster信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 获取老的configDB配置
    mongos_nodes = {}
    old_config_node = ""
    new_config_node = ""
    if info["mongo_config"]:
        sub_get_kwargs.get_cluster_info_deinstall(cluster_id=info["mongo_config"][0]["instances"][0]["cluster_id"])
        config_port = info["mongo_config"][0]["instances"][0]["port"]
        old_config_node = "{}:{}".format(info["mongo_config"][0]["ip"], config_port)
        new_config_node = "{}:{}".format(info["mongo_config"][0]["target"]["ip"], config_port)
        mongos_nodes = sub_get_kwargs.payload["mongos_nodes"]

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取信息
    sub_get_kwargs.get_host_replace(mongodb_type=ClusterType.MongoShardedCluster.value, info=info)
    if info["mongo_config"]:
        sub_get_kwargs.get_mongos_host_replace()

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

    # 进行shard和config替换——并行
    sub_sub_pipelines = []
    # 替换config 以ip为维度
    for config_info_by_ip in info["mongo_config"]:
        sub_sub_pipeline = replicaset_replace(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            info=config_info_by_ip,
            cluster_role=MongoDBClusterRole.ConfigSvr.value,
        )
        sub_sub_pipelines.append(sub_sub_pipeline)
    # 替换shard 以ip为维度
    for shard_info_by_ip in info["mongodb"]:
        sub_sub_pipeline = replicaset_replace(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_kwargs=sub_get_kwargs,
            info=shard_info_by_ip,
            cluster_role=MongoDBClusterRole.ShardSvr.value,
        )
        sub_sub_pipelines.append(sub_sub_pipeline)
    if sub_sub_pipelines:
        sub_pipeline.add_parallel_sub_pipeline(sub_sub_pipelines)

    # 修改mongos参数文件 只修改参数，不重启进程
    if info["mongo_config"]:
        act_lists = []
        for mongos_node in mongos_nodes:
            mongos_node["role"] = MongoDBInstanceType.MongoS.value
            kwargs = sub_get_kwargs.get_instance_restart_kwargs(
                host=mongos_node,
                cache_size_gb=0,
                mongos_conf_db_old=old_config_node,
                mongos_conf_db_new=new_config_node,
                cluster_id=info["mongo_config"][0]["instances"][0]["cluster_id"],
                instance=mongos_node,
                only_change_param=True,
            )
            act_lists.append(
                {
                    "act_name": _("MongoDB-{}-mongos修改参数".format(mongos_node["ip"])),
                    "act_component_code": ExecuteDBActuatorJobComponent.code,
                    "kwargs": kwargs,
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=act_lists)

    # 替换mongos 以ip为维度
    if info["mongos"]:
        sub_sub_pipelines = []
        for mongos_info_by_ip in info["mongos"]:
            for mongos_instance in mongos_info_by_ip["instances"]:
                sub_get_kwargs.db_instance = mongos_instance
                sub_sub_pipeline = mongos_replace(
                    root_id=root_id, ticket_data=ticket_data, sub_sub_kwargs=sub_get_kwargs, info=mongos_info_by_ip
                )
                sub_sub_pipelines.append(sub_sub_pipeline)
        sub_pipeline.add_parallel_sub_pipeline(sub_sub_pipelines)
        # mongos修改db_meta数据
        info["db_type"] = "mongos"
        info["created_by"] = sub_get_kwargs.payload.get("created_by")
        info["bk_biz_id"] = sub_get_kwargs.payload.get("bk_biz_id")
        kwargs = sub_get_kwargs.get_change_meta_replace_kwargs(info=info, instance={})
        sub_pipeline.add_act(
            act_name=_("MongoDB-mongos修改meta"), act_component_code=CMRMongoDBMetaComponent.code, kwargs=kwargs
        )
    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--cluster整机替换"))
