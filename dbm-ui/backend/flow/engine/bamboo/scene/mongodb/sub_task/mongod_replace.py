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
from backend.flow.consts import MongoDBClusterRole, MongoDBInstanceType, MongoDBManagerUser
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mongodb.add_domain_to_dns import ExecAddDomainToDnsOperationComponent
from backend.flow.plugins.components.collections.mongodb.add_password_to_db import (
    ExecAddPasswordToDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_domain_from_dns import (
    ExecDeleteDomainFromDnsOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_password_from_db import (
    ExecDeletePasswordFromDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def mongod_replace(
    root_id: str, ticket_data: Optional[Dict], sub_sub_kwargs: ActKwargs, cluster_role: str, info: dict
) -> SubBuilder:
    """
    mongod替换流程
    """

    # 获取变量
    sub_sub_get_kwargs = deepcopy(sub_sub_kwargs)

    # 创建子流程
    sub_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取参数
    new_node = info["target"]
    sub_sub_get_kwargs.payload["app"] = sub_sub_get_kwargs.payload["bk_app_abbr"]
    sub_sub_get_kwargs.replicaset_info["port"] = sub_sub_get_kwargs.db_instance["port"]
    if cluster_role:
        sub_sub_get_kwargs.cluster_type = ClusterType.MongoShardedCluster.value
        cluster_name = sub_sub_get_kwargs.db_instance["seg_range"]
        sub_sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoShardedCluster.value
        sub_sub_get_kwargs.payload["set_id"] = sub_sub_get_kwargs.db_instance["seg_range"]
        sub_sub_get_kwargs.payload["key_file"] = sub_sub_get_kwargs.get_key_file(
            cluster_name=sub_sub_get_kwargs.db_instance["cluster_name"]
        )
        sub_sub_get_kwargs.payload["config_nodes"] = []
        sub_sub_get_kwargs.payload["shards_nodes"] = []
        sub_sub_get_kwargs.payload["mongos_nodes"] = []
        if cluster_role == MongoDBClusterRole.ConfigSvr.value:
            sub_sub_get_kwargs.payload["config_nodes"] = [
                {
                    "ip": info["ip"],
                    "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
                    "port": sub_sub_get_kwargs.db_instance["port"],
                    "bk_cloud_id": info["bk_cloud_id"],
                }
            ]
        elif cluster_role == MongoDBClusterRole.ShardSvr.value:
            shard_nodes = {
                "nodes": [
                    {
                        "ip": info["ip"],
                        "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
                        "port": sub_sub_get_kwargs.db_instance["port"],
                        "bk_cloud_id": info["bk_cloud_id"],
                    }
                ]
            }

            sub_sub_get_kwargs.payload["shards_nodes"].append(shard_nodes)
    else:
        sub_sub_get_kwargs.cluster_type = ClusterType.MongoReplicaSet.value
        cluster_name = sub_sub_get_kwargs.db_instance["cluster_name"]
        sub_sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoReplicaSet.value
        sub_sub_get_kwargs.payload["set_id"] = sub_sub_get_kwargs.db_instance["cluster_name"]
        sub_sub_get_kwargs.replicaset_info["key_file"] = sub_sub_get_kwargs.get_key_file(
            cluster_name=sub_sub_get_kwargs.db_instance["cluster_name"]
        )
    sub_sub_get_kwargs.replicaset_info["set_id"] = cluster_name
    sub_sub_get_kwargs.replicaset_info["nodes"] = [
        {
            "ip": new_node["ip"],
            "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
            "bk_cloud_id": info["bk_cloud_id"],
            "port": sub_sub_get_kwargs.db_instance["port"],
        }
    ]
    sub_sub_get_kwargs.payload["nodes"] = [
        {
            "ip": info["ip"],
            "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
            "port": sub_sub_get_kwargs.db_instance["port"],
            "bk_cloud_id": info["bk_cloud_id"],
        }
    ]
    sub_sub_get_kwargs.payload["bk_cloud_id"] = info["bk_cloud_id"]

    # mognod安装
    kwargs = sub_sub_get_kwargs.get_install_mongod_kwargs(node=new_node, cluster_role=cluster_role)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-mongod安装-{}:{}".format(new_node["ip"], str(sub_sub_get_kwargs.db_instance["port"]))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # mognod替换
    kwargs = sub_sub_get_kwargs.get_instance_replace_kwargs(info=info, source_down=False)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-mongod替换"),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    # 更改dns
    # 添加新的dns
    if not cluster_role:
        kwargs = sub_sub_get_kwargs.get_add_domain_to_dns_kwargs(cluster=False)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-添加新实例的domain到dns"),
            act_component_code=ExecAddDomainToDnsOperationComponent.code,
            kwargs=kwargs,
        )
        # 删除老的dns
        kwargs = sub_sub_get_kwargs.get_delete_domain_kwargs()
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-删除老实例的domain指向"),
            act_component_code=ExecDeleteDomainFromDnsOperationComponent.code,
            kwargs=kwargs,
        )

    # 密码服务修改密码
    # 添加新实例密码
    kwargs = sub_sub_get_kwargs.get_add_password_to_db_kwargs(
        usernames=[
            MongoDBManagerUser.DbaUser.value,
            MongoDBManagerUser.AppDbaUser.value,
            MongoDBManagerUser.MonitorUser.value,
            MongoDBManagerUser.AppMonitorUser.value,
        ],
        info=sub_sub_get_kwargs.replicaset_info,
    )
    # 用户获取密码
    kwargs = sub_sub_get_kwargs.get_password_from_db(info=kwargs)
    # 是否是部署单据
    kwargs["create"] = False
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-保存新实例的dba用户及额外管理用户密码"),
        act_component_code=ExecAddPasswordToDBOperationComponent.code,
        kwargs=kwargs,
    )
    # 删除老实例密码
    kwargs = sub_sub_get_kwargs.get_delete_pwd_kwargs()
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-删除老实例的dba用户及额外管理用户密码"),
        act_component_code=ExecDeletePasswordFromDBOperationComponent.code,
        kwargs=kwargs,
    )

    # 下架老实例
    kwargs = sub_sub_get_kwargs.get_mongo_deinstall_kwargs(
        node_info=sub_sub_get_kwargs.payload["nodes"][0],
        instance_type=MongoDBInstanceType.MongoD.value,
        nodes_info=sub_sub_get_kwargs.payload["nodes"],
    )
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-老实例下架-{}:{}".format(info["ip"], str(sub_sub_get_kwargs.db_instance["port"]))),
        act_component_code=ExecuteDBActuatorJobComponent.code,
        kwargs=kwargs,
    )

    return sub_sub_pipeline.build_sub_process(
        sub_name=_("MongoDB--mongod替换--{}:{}".format(info["ip"], str(sub_sub_get_kwargs.db_instance["port"])))
    )
