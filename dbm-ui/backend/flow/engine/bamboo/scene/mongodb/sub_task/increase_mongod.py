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

from backend.flow.consts import MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.add_domain_to_dns import ExecAddDomainToDnsOperationComponent
from backend.flow.plugins.components.collections.mongodb.add_password_to_db import (
    ExecAddPasswordToDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def increase_mongod(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict, cluster_role: str
) -> SubBuilder:
    """
    replicaset 增加节点流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 设置参数
    node = sub_get_kwargs.db_instance
    sub_get_kwargs.replicaset_info["nodes"] = [
        {
            "ip": node["ip"],
            "domain": node.get("domain", ""),
            "bk_cloud_id": node["bk_cloud_id"],
            "port": node["port"],
        }
    ]
    if not cluster_role:
        # 获取集群信息并计算对应关系
        sub_get_kwargs.get_cluster_info_deinstall(cluster_id=info["cluster_id"])

        # 获取密码
        get_password = {}
        get_password["usernames"] = sub_get_kwargs.manager_users
        sub_get_kwargs.payload["passwords"] = sub_get_kwargs.get_password_from_db(info=get_password)["passwords"]

        # 获取key_file
        sub_get_kwargs.cluster_type = sub_get_kwargs.payload["cluster_type"]
        sub_get_kwargs.replicaset_info["key_file"] = sub_get_kwargs.get_conf(
            cluster_name=sub_get_kwargs.payload["cluster_name"]
        )["key_file"]

        # 设置参数
        sub_get_kwargs.replicaset_info["set_id"] = sub_get_kwargs.payload["set_id"]
        shard_name = sub_get_kwargs.payload["cluster_name"]
        operation_node = sub_get_kwargs.payload["nodes"][0]
    else:
        shard_name = node["seg_range"]
        sub_get_kwargs.replicaset_info["set_id"] = shard_name
        for shard in sub_get_kwargs.payload["shards_nodes"]:
            if shard["shard"] == shard_name:
                sub_get_kwargs.payload["operation_node"] = shard["nodes"][0]
                break
        operation_node = sub_get_kwargs.payload["operation_node"]

    sub_get_kwargs.replicaset_info["port"] = node["port"]
    # 新节点作为执行操作节点
    add_node_info = {
        "exec_ip": node["ip"],
        "exec_bk_cloud_id": node["bk_cloud_id"],
        "ip": operation_node["ip"],
        "port": operation_node["port"],
        "bk_cloud_id": operation_node["bk_cloud_id"],
        "admin_user": MongoDBManagerUser.DbaUser.value,
        "admin_password": sub_get_kwargs.payload["passwords"][MongoDBManagerUser.DbaUser.value],
        "target": node,
    }

    # mongod安装
    kwargs = sub_get_kwargs.get_install_mongod_kwargs(node=node, cluster_role=cluster_role)
    sub_pipeline.add_act(
        act_name=_("MongoDB-{}-mongod安装".format(node["ip"])),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # 添加到复制集中
    kwargs = sub_get_kwargs.get_increase_node_kwargs(info=add_node_info)
    sub_pipeline.add_act(
        act_name=_("MongoDB-添加node"),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # 添加新增实例dns
    if not cluster_role:
        kwargs = sub_get_kwargs.get_add_domain_to_dns_kwargs(cluster=False)
        sub_pipeline.add_act(
            act_name=_("MongoDB-添加新实例的domain到dns"),
            act_component_code=ExecAddDomainToDnsOperationComponent.code,
            kwargs=kwargs,
        )

    # 保存新实例密码
    kwargs = sub_get_kwargs.get_add_password_to_db_kwargs(
        usernames=sub_get_kwargs.manager_users,
        info=sub_get_kwargs.replicaset_info,
    )
    # 用户获取密码
    kwargs["passwords"] = sub_get_kwargs.payload["passwords"]
    # 是否是部署单据
    kwargs["create"] = False
    sub_pipeline.add_act(
        act_name=_("MongoDB-保存新实例的dba用户及额外管理用户密码"),
        act_component_code=ExecAddPasswordToDBOperationComponent.code,
        kwargs=kwargs,
    )

    return sub_pipeline.build_sub_process(
        sub_name=_("MongoDB--{}增加node{}:{}".format(shard_name, node["ip"], node["port"]))
    )
