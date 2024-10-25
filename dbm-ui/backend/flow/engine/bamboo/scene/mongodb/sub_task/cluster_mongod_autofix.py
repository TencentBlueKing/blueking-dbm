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
from backend.flow.plugins.components.collections.mongodb.add_password_to_db import (
    ExecAddPasswordToDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.delete_password_from_db import (
    ExecDeletePasswordFromDBOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.instance_deinstall_ticket import (
    ExecInstanceDeInstallTicketOperationComponent,
)
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def mongod_autofix(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_sub_kwargs: ActKwargs,
    cluster_role: str,
    info: dict,
) -> SubBuilder:
    """
    mongod自愈流程
    """

    # 获取变量
    sub_sub_get_kwargs = deepcopy(sub_sub_kwargs)

    # 创建子流程
    sub_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取参数
    down = info.get("down")  # 机器是否down
    new_node = info["target"]
    sub_sub_get_kwargs.payload["app"] = sub_sub_get_kwargs.payload["bk_app_abbr"]
    sub_sub_get_kwargs.replicaset_info = {}
    sub_sub_get_kwargs.replicaset_info["port"] = sub_sub_get_kwargs.db_instance["port"]
    sub_sub_get_kwargs.cluster_type = ClusterType.MongoShardedCluster.value
    cluster_name = sub_sub_get_kwargs.db_instance["seg_range"]
    sub_sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoShardedCluster.value
    sub_sub_get_kwargs.payload["set_id"] = sub_sub_get_kwargs.db_instance["seg_range"]
    sub_sub_get_kwargs.payload["key_file"] = sub_sub_get_kwargs.get_conf(
        cluster_name=sub_sub_get_kwargs.db_instance["cluster_name"]
    )["key_file"]
    sub_sub_get_kwargs.payload["config_nodes"] = []
    sub_sub_get_kwargs.payload["shards_nodes"] = []
    sub_sub_get_kwargs.payload["mongos_nodes"] = []
    # 获取配置
    conf = sub_sub_get_kwargs.get_conf(cluster_name=sub_sub_get_kwargs.db_instance["cluster_name"])
    if cluster_role == MongoDBClusterRole.ConfigSvr.value:
        sub_sub_get_kwargs.payload["config_nodes"] = [
            {
                "ip": info["ip"],
                "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
                "port": sub_sub_get_kwargs.db_instance["port"],
                "bk_cloud_id": info["bk_cloud_id"],
            }
        ]
        sub_sub_get_kwargs.replicaset_info["cacheSizeGB"] = conf["config_cacheSizeGB"]
        sub_sub_get_kwargs.replicaset_info["oplogSizeMB"] = conf["config_oplogSizeMB"]
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
        # shard直接获取配置
        sub_sub_get_kwargs.replicaset_info["cacheSizeGB"] = conf["cacheSizeGB"]
        sub_sub_get_kwargs.replicaset_info["oplogSizeMB"] = conf["oplogSizeMB"]
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
            "role": MongoDBInstanceType.MongoD.value,
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
    kwargs = sub_sub_get_kwargs.get_instance_replace_kwargs(info=info, source_down=down)
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-mongod替换"),
        act_component_code=ExecuteDBActuatorJobComponent.code,
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

    # 老实例提下架单
    kwargs = {
        "infos": sub_sub_get_kwargs.payload["nodes"],
        "creator": sub_sub_get_kwargs.payload["created_by"],
        "bk_biz_id": sub_sub_get_kwargs.payload["bk_biz_id"],
    }
    sub_sub_pipeline.add_act(
        act_name=_("MongoDB-实例下架提单"),
        act_component_code=ExecInstanceDeInstallTicketOperationComponent.code,
        kwargs=kwargs,
    )
    return sub_sub_pipeline.build_sub_process(
        sub_name=_("MongoDB--mongod自愈--{}:{}".format(info["ip"], str(sub_sub_get_kwargs.db_instance["port"])))
    )
