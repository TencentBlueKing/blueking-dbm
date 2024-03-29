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

from backend.flow.consts import MongoDBInstanceType, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.delete_domain_from_dns import (
    ExecDeleteDomainFromDnsOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_password_from_db import (
    ExecDeletePasswordFromDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.mongodb_scale_repls_meta import MongoScaleReplsMetaComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def reduce_mongod(root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, cluster: bool) -> SubBuilder:
    """
    replicaset 减少节点流程
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 设置参数
    node = sub_get_kwargs.db_instance
    sub_get_kwargs.replicaset_info = {}
    sub_get_kwargs.replicaset_info["nodes"] = [
        {
            "ip": node["ip"],
            "domain": node.get("domain", ""),
            "bk_cloud_id": node["bk_cloud_id"],
            "port": node["port"],
        }
    ]
    sub_get_kwargs.payload["nodes"] = []
    sub_get_kwargs.payload["nodes"].append(node)
    if cluster:
        sub_get_kwargs.payload["mongos_nodes"] = []
        sub_get_kwargs.payload["config_nodes"] = []
        sub_get_kwargs.payload["shards_nodes"] = []
        sub_get_kwargs.payload["shards_nodes"].append({"nodes": sub_get_kwargs.payload["nodes"]})
    else:
        # 获取密码
        get_password = {}
        get_password["usernames"] = sub_get_kwargs.manager_users
        sub_get_kwargs.payload["passwords"] = sub_get_kwargs.get_password_from_db(info=get_password)["passwords"]

    # 移除节点作为执行操作节点
    remove_node_info = {
        "exec_ip": node["ip"],
        "exec_bk_cloud_id": node["bk_cloud_id"],
        "ip": node["ip"],
        "port": node["port"],
        "bk_cloud_id": node["bk_cloud_id"],
        "admin_user": MongoDBManagerUser.DbaUser.value,
        "admin_password": sub_get_kwargs.payload["passwords"][MongoDBManagerUser.DbaUser.value],
        "source": node,
    }

    # 从复制集中移除
    kwargs = sub_get_kwargs.get_reduce_node_kwargs(info=remove_node_info)
    sub_pipeline.add_act(
        act_name=_("MongoDB-移除node"),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # mongod下架
    kwargs = sub_get_kwargs.get_mongo_deinstall_kwargs(
        node_info=node,
        instance_type=MongoDBInstanceType.MongoD.value,
        nodes_info=[node],
        force=True,
    )
    sub_pipeline.add_act(
        act_name=_("MongoDB-{}-mongod下架".format(node["ip"])),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # 实例dns删除
    if not cluster:
        kwargs = sub_get_kwargs.get_delete_domain_kwargs()
        sub_pipeline.add_act(
            act_name=_("MongoDB-删除node的domain指向"),
            act_component_code=ExecDeleteDomainFromDnsOperationComponent.code,
            kwargs=kwargs,
        )

    # 删除实例密码
    kwargs = sub_get_kwargs.get_delete_pwd_kwargs()
    sub_pipeline.add_act(
        act_name=_("MongoDB-删除node的dba用户及额外管理用户密码"),
        act_component_code=ExecDeletePasswordFromDBOperationComponent.code,
        kwargs=kwargs,
    )

    # 修改meta
    kwargs = sub_get_kwargs.get_meta_scale_node_kwargs(info=[node], increase=False)
    sub_pipeline.add_act(
        act_name=_("MongoDB-修改meta"),
        act_component_code=MongoScaleReplsMetaComponent.code,
        kwargs=kwargs,
    )

    return sub_pipeline.build_sub_process(
        sub_name=_("MongoDB--{}减少node{}:{}".format(node["cluster_name"], node["ip"], node["port"]))
    )
