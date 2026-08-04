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

from backend.flow.consts import MongoDBInstanceType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.multi_instance_deinstall import multi_instance_deinstall
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mongodb.cluster_reduce_shard_meta import (
    ExecReduceShardMetaOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_password_from_db import (
    ExecDeletePasswordFromDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def cluster_reduce_shard(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, reduce_shard_info: dict
) -> SubBuilder:
    """
    单个 cluster 减少分片流程：
    介质/目录 → removeShard → Pause → 多实例卸载 → 删密码 → meta 清理 → 关闭 balancer
    """

    sub_get_kwargs = deepcopy(sub_kwargs)
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    sub_get_kwargs.payload["bk_cloud_id"] = reduce_shard_info["bk_cloud_id"]
    sub_get_kwargs.payload["hosts"] = reduce_shard_info["hosts"]
    sub_get_kwargs.payload["mongos"] = reduce_shard_info["mongos"]
    sub_get_kwargs.payload["reduce_shards"] = reduce_shard_info["reduce_shards"]
    sub_get_kwargs.payload["db_version"] = reduce_shard_info.get("db_version") or ""
    sub_get_kwargs.payload["nodes"] = reduce_shard_info["mongos"]["nodes"]

    # 介质下发（mongos + 待删 shard 主机）
    kwargs = sub_get_kwargs.get_send_media_kwargs(media_type="actuator")
    sub_pipeline.add_act(
        act_name=_("MongoDB-介质下发"), act_component_code=ExecSendMediaOperationComponent.code, kwargs=kwargs
    )

    # 创建原子任务执行目录
    kwargs = sub_get_kwargs.get_create_dir_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-创建原子任务执行目录"), act_component_code=ExecuteDBActuatorJobComponent.code, kwargs=kwargs
    )

    # 从 mongos 取管理密码
    get_password = {"usernames": sub_get_kwargs.manager_users}
    sub_get_kwargs.payload["passwords"] = sub_get_kwargs.get_password_from_db(info=get_password)["passwords"]

    # 打开 balancer，便于排水（不等待均衡完成）
    kwargs = sub_get_kwargs.get_balancer_kwargs(open=True, wait_for_balance=False)
    sub_pipeline.add_act(
        act_name=_("MongoDB--打开balancer"),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # removeShard 排水
    kwargs = sub_get_kwargs.get_remove_shard_from_cluster_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB--从cluster移除shards"),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # 人工确认排水与数据安全
    sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

    # 卸载待删 shard 全部 mongod
    deinstall_pipeline = multi_instance_deinstall(
        root_id=root_id,
        ticket_data=ticket_data,
        sub_kwargs=sub_get_kwargs,
        old_hosts=reduce_shard_info["old_hosts"],
        old_instances=reduce_shard_info["old_instances"],
        instance_type=MongoDBInstanceType.MongoD.value,
    )
    sub_pipeline.add_sub_pipeline(sub_flow=deinstall_pipeline)

    # 删除密码
    kwargs = sub_get_kwargs.get_reduce_shard_delete_pwd_kwargs(reduce_shard_info["old_instances"])
    sub_pipeline.add_act(
        act_name=_("MongoDB--删除实例密码"),
        act_component_code=ExecDeletePasswordFromDBOperationComponent.code,
        kwargs=kwargs,
    )

    # DBMeta 清理
    kwargs = sub_get_kwargs.get_reduce_shard_to_meta_kwargs(info=reduce_shard_info)
    sub_pipeline.add_act(
        act_name=_("MongoDB--减少shard清理meta"),
        act_component_code=ExecReduceShardMetaOperationComponent.code,
        kwargs=kwargs,
    )

    # 关闭 balancer
    kwargs = sub_get_kwargs.get_balancer_kwargs(open=False)
    sub_pipeline.add_act(
        act_name=_("MongoDB--关闭balancer"),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    return sub_pipeline.build_sub_process(
        sub_name=_("MongoDB--cluster:{}减少shard".format(reduce_shard_info["cluster_name"]))
    )
