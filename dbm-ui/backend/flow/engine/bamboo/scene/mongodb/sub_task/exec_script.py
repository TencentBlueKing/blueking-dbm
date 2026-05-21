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

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.engine.bamboo.scene.common.atom_jobs.set_dns_sub_job import set_dns_atom_job
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.common_act_dataclass import DNSContext
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs as RedisActKwargs


def exec_script(root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict) -> SubBuilder:
    """
    单个分片集群或多个副本集执行脚本流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 设置参数
    cluster_type = info["cluster_type"]
    sub_get_kwargs.cluster_type = cluster_type
    sub_get_kwargs.payload["db_version"] = info["db_version"]
    sub_get_kwargs.payload["hosts"] = info["hosts"]
    ip = info["hosts"][0]["ip"]
    sub_get_kwargs.payload["bk_cloud_id"] = info["bk_cloud_id"]
    sub_get_kwargs.payload["instance_type"] = info["instance_type"]
    sub_get_kwargs.payload["region"] = info["region"]
    admin_user = info["admin_user"]

    # 介质下发
    kwargs = sub_get_kwargs.get_send_media_kwargs(media_type="actuator")
    sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 设置dns解析
    redis_actkwargs = RedisActKwargs()
    redis_actkwargs.cluster = {}
    redis_actkwargs.set_trans_data_dataclass = DNSContext.__name__
    redis_actkwargs.is_update_trans_data = True
    redis_actkwargs.bk_cloud_id = sub_get_kwargs.payload["bk_cloud_id"]
    kwargs = sub_get_kwargs.get_set_dns_resolv_kwargs()
    sub_sub_pipeline = set_dns_atom_job(
        root_id=sub_get_kwargs.root_id, ticket_data=sub_get_kwargs.payload, act_kwargs=redis_actkwargs, param=kwargs
    )
    sub_pipeline.add_sub_pipeline(sub_sub_pipeline)

    # 创建原子任务执行目录
    kwargs = sub_get_kwargs.get_create_dir_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 分发脚本文件
    kwargs = sub_get_kwargs.get_send_script_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-脚本文件下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 执行脚本
    clusterids = []
    if cluster_type == ClusterType.MongoShardedCluster.value:
        sub_get_kwargs.payload["port"] = info["port"]
        sub_get_kwargs.payload["admin_password"] = info["admin_password"]
        cluster_id = info["cluster_id"]
        clusterids.append(cluster_id)
        kwargs = sub_get_kwargs.get_exec_script_kwargs(cluster_id=cluster_id, admin_user=admin_user)
        sub_pipeline.add_act(
            act_name=_("MongoDB-cluster_id:{}-{}:{}-执行脚本".format(str(cluster_id), ip, str(info["port"]))),
            act_component_code=ExecuteDBActuatorJobComponent.code,
            kwargs=kwargs,
        )
    elif cluster_type == ClusterType.MongoReplicaSet.value:
        for instance in info["instance_info"]:
            sub_get_kwargs.payload["port"] = instance["port"]
            sub_get_kwargs.payload["admin_password"] = instance["admin_password"]
            cluster_id = instance["cluster_id"]
            clusterids.append(cluster_id)
            kwargs = sub_get_kwargs.get_exec_script_kwargs(cluster_id=cluster_id, admin_user=admin_user)
            sub_pipeline.add_act(
                act_name=_("MongoDB-cluster_id:{}-{}:{}-执行脚本".format(str(cluster_id), ip, str(instance["port"]))),
                act_component_code=ExecuteDBActuatorJobComponent.code,
                kwargs=kwargs,
            )

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--执行脚本--clusterids:{}-ip:{}".format(clusterids, ip)))
