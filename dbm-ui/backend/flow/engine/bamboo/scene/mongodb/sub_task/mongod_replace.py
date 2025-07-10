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

from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import MongoDBClusterRole, MongoDBInstanceType, MongoDBManagerUser, MongoInstanceDbmonType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.pause import PauseComponent
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
from backend.flow.plugins.components.collections.mongodb.fast_exec_script import MongoFastExecScriptComponent
from backend.flow.plugins.components.collections.mongodb.mongodb_capcity_chgs_meta import MongoDBCapcityMetaComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def mongod_replace(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_sub_kwargs: ActKwargs,
    cluster_role: str,
    info: dict,
    mongod_scale: bool,
) -> SubBuilder:
    """
    mongod替换流程
    """

    # 获取变量
    sub_sub_get_kwargs = deepcopy(sub_sub_kwargs)

    # 创建子流程
    sub_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取参数
    instance_role_exclude_backup = [
        InstanceRole.MONGO_M1.value,
        InstanceRole.MONGO_M2.value,
        InstanceRole.MONGO_M3.value,
        InstanceRole.MONGO_M4.value,
        InstanceRole.MONGO_M5.value,
        InstanceRole.MONGO_M6.value,
        InstanceRole.MONGO_M7.value,
        InstanceRole.MONGO_M8.value,
        InstanceRole.MONGO_M9.value,
        InstanceRole.MONGO_M10.value,
    ]
    down = info.get("down")  # 机器是否down
    new_node = info["target"]  # 新节点信息
    sub_sub_get_kwargs.payload["app"] = sub_sub_get_kwargs.payload["bk_app_abbr"]
    add_node_info = {}
    remove_node_info = {}

    if not mongod_scale:
        sub_sub_get_kwargs.replicaset_info = {}
    sub_sub_get_kwargs.replicaset_info["port"] = sub_sub_get_kwargs.db_instance["port"]
    # 默认强制下架实例
    force = True
    if cluster_role:
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
        # 整机替换获取配置
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
            if not mongod_scale:
                # 整机替换shard直接获取configdb保存cachesize 和 oplogsize 的配置
                sub_sub_get_kwargs.replicaset_info["cacheSizeGB"] = conf["cacheSizeGB"]
                sub_sub_get_kwargs.replicaset_info["oplogSizeMB"] = conf["oplogSizeMB"]
        # 删除老实例密码使用
        sub_sub_get_kwargs.payload["nodes"] = [
            {
                "ip": info["ip"],
                "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
                "port": sub_sub_get_kwargs.db_instance["port"],
                "bk_cloud_id": info["bk_cloud_id"],
            }
        ]
        # 下架节点信息
        nodes_info = [
            {
                "ip": info["ip"],
                "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
                "port": sub_sub_get_kwargs.db_instance["port"],
                "bk_cloud_id": info["bk_cloud_id"],
            }
        ]
        node_info = nodes_info[0]
    else:
        # 副本集下架需要检查连接
        force = False
        if mongod_scale:
            force = True
        sub_sub_get_kwargs.cluster_type = ClusterType.MongoReplicaSet.value
        cluster_name = sub_sub_get_kwargs.db_instance["cluster_name"]
        sub_sub_get_kwargs.payload["cluster_type"] = ClusterType.MongoReplicaSet.value
        sub_sub_get_kwargs.payload["set_id"] = cluster_name
        # 副本集直接获取配置
        conf = sub_sub_get_kwargs.get_conf(cluster_name=cluster_name)
        sub_sub_get_kwargs.replicaset_info["key_file"] = conf["key_file"]
        if not mongod_scale:
            sub_sub_get_kwargs.replicaset_info["cacheSizeGB"] = conf["cacheSizeGB"]
            sub_sub_get_kwargs.replicaset_info["oplogSizeMB"] = conf["oplogSizeMB"]
        # 删除老实例密码使用
        sub_sub_get_kwargs.payload["nodes"] = [
            {
                "ip": info["ip"],
                "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
                "port": sub_sub_get_kwargs.db_instance["port"],
                "bk_cloud_id": info["bk_cloud_id"],
            }
        ]
        # 副本集添加新节点信息 新节点作为执行操作节点
        # 获取密码
        get_password = {}
        get_password["usernames"] = sub_sub_get_kwargs.manager_users
        sub_sub_get_kwargs.payload["passwords"] = sub_sub_get_kwargs.get_password_from_db(info=get_password)[
            "passwords"
        ]
        admin_user = MongoDBManagerUser.DbaUser.value
        admin_password = sub_sub_get_kwargs.payload["passwords"][admin_user]
        port = sub_sub_get_kwargs.db_instance["port"]
        # 添加新节点
        target = {
            "ip": new_node["ip"],
            "port": port,
            "priority": "",
            "hidden": "",
        }
        add_node_info = {
            "exec_ip": new_node["ip"],
            "exec_bk_cloud_id": new_node["bk_cloud_id"],
            "ip": "",
            "port": port,
            "bk_cloud_id": info["bk_cloud_id"],
            "admin_user": admin_user,
            "admin_password": admin_password,
            "target": target,
        }
        # 副本集移除老节点信息 移除节点作为执行操作节点
        source = {
            "ip": info["ip"],
            "port": port,
        }
        remove_node_info = {
            "exec_ip": new_node["ip"],
            "exec_bk_cloud_id": new_node["bk_cloud_id"],
            "ip": new_node["ip"],
            "port": port,
            "bk_cloud_id": info["bk_cloud_id"],
            "admin_user": admin_user,
            "admin_password": admin_password,
            "source": source,
        }
        nodes_info = []
        node_info = source
        nodes_info.append(target)
        # 获取副本集所有的节点信息
        for node in sub_sub_get_kwargs.replicaset_mongod_replace_get_node(
            cluster_id=sub_sub_get_kwargs.db_instance["cluster_id"]
        ):
            nodes_info.append(
                {
                    "ip": node["ip"],
                    "port": node["port"],
                }
            )
            if node["ip"] == info["ip"] and node["instance_role"] in instance_role_exclude_backup:
                add_node_info["target"]["priority"] = "1"
                add_node_info["target"]["hidden"] = "0"
            elif node["ip"] == info["ip"] and node["instance_role"] == InstanceRole.MONGO_BACKUP.value:
                add_node_info["target"]["priority"] = "0"
                add_node_info["target"]["hidden"] = "1"
        # 主备切换参数
        step_down_info = {
            "exec_ip": "",
            "exec_bk_cloud_id": 0,
            "ip": "",
            "port": port,
            "target_ip": info["ip"],
            "admin_user": admin_user,
            "admin_password": admin_password,
        }

    # 公共参数
    sub_sub_get_kwargs.replicaset_info["set_id"] = cluster_name
    sub_sub_get_kwargs.replicaset_info["nodes"] = [
        {
            "ip": new_node["ip"],
            "domain": sub_sub_get_kwargs.db_instance.get("domain", ""),
            "bk_cloud_id": info["bk_cloud_id"],
            "port": sub_sub_get_kwargs.db_instance["port"],
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

    # 整机替换执行ip不为替换的ip  容量变更为source ip
    if not mongod_scale:
        exec_info = sub_sub_get_kwargs.mongod_replace_get_exec_ip(
            cluster_type=sub_sub_get_kwargs.cluster_type,
            cluster_role=cluster_role,
            source_ip=info["ip"],
            instance=sub_sub_get_kwargs.db_instance,
        )
        exec_ip = exec_info["ip"]
        exec_ip_bk_cloud_id = exec_info["bk_cloud_id"]
    else:
        exec_ip = info["ip"]
        exec_ip_bk_cloud_id = info["bk_cloud_id"]

    # mognod替换
    # 副本集 mongod 整机替换 添加 node，容量变更
    if not cluster_role:
        # 人工确认
        sub_sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
        # 检查源端是否为主，如果为主则进行主备切换
        step_down_info["exec_ip"] = exec_ip
        step_down_info["exec_bk_cloud_id"] = exec_ip_bk_cloud_id
        step_down_info["ip"] = exec_ip
        kwargs = sub_sub_get_kwargs.get_step_down_kwargs(info=step_down_info)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-主备切换-{}:{}".format(info["ip"], str(sub_sub_get_kwargs.db_instance["port"]))),
            act_component_code=ExecuteDBActuatorJobComponent.code,
            kwargs=kwargs,
        )
        # 添加新节点到副本集中
        # 操作ip为非需要替换的ip
        add_node_info["ip"] = exec_ip
        kwargs = sub_sub_get_kwargs.get_res_replace_add_node_kwargs(info=add_node_info)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-添加node-{}:{}".format(new_node["ip"], str(sub_sub_get_kwargs.db_instance["port"]))),
            act_component_code=ExecuteDBActuatorJobComponent.code,
            kwargs=kwargs,
        )
    else:
        # cluster mongod 整机替换，cluster 容量变更
        kwargs = sub_sub_get_kwargs.get_instance_replace_kwargs(exec_ip=exec_ip, info=info, source_down=down)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-mongod替换"),
            act_component_code=ExecuteDBActuatorJobComponent.code,
            kwargs=kwargs,
        )

    # 副本集更改dns
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

    # 修改meta信息
    if mongod_scale:
        kwargs = sub_sub_get_kwargs.get_scale_change_meta(info=info, instance=sub_sub_get_kwargs.db_instance)
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-mongod修改meta"), act_component_code=MongoDBCapcityMetaComponent.code, kwargs=kwargs
        )

    if not down:
        # 下架老实例
        if not cluster_role:
            # 人工确认
            sub_sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            # 从复制集中移除老节点
            kwargs = sub_sub_get_kwargs.get_reduce_node_kwargs(info=remove_node_info)
            sub_sub_pipeline.add_act(
                act_name=_(
                    "MongoDB-移除node-{}:{}".format(node_info["ip"], str(sub_sub_get_kwargs.db_instance["port"]))
                ),
                act_component_code=ExecuteDBActuatorJobComponent.code,
                kwargs=kwargs,
            )
        # 老实例关闭 dbmon
        kwargs_delete_dbmon = sub_sub_get_kwargs.get_dbmon_operation_kwargs(
            node_info=node_info, operation_type=MongoInstanceDbmonType.DeleteDbmon
        )
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-{}:{}-删除dbmon".format(node_info["ip"], str(node_info["port"]))),
            act_component_code=MongoFastExecScriptComponent.code,
            kwargs=kwargs_delete_dbmon,
        )

        # 下架
        kwargs = sub_sub_get_kwargs.get_mongo_deinstall_kwargs(
            node_info=node_info,
            instance_type=MongoDBInstanceType.MongoD.value,
            nodes_info=nodes_info,
            force=force,
            rename_dir=True,
        )
        sub_sub_pipeline.add_act(
            act_name=_("MongoDB-老实例下架-{}:{}".format(info["ip"], str(sub_sub_get_kwargs.db_instance["port"]))),
            act_component_code=ExecuteDBActuatorJobComponent.code,
            kwargs=kwargs,
        )
    # 老实例提下架单 TODO
    return sub_sub_pipeline.build_sub_process(
        sub_name=_("MongoDB--mongod替换--{}:{}".format(info["ip"], str(sub_sub_get_kwargs.db_instance["port"])))
    )
