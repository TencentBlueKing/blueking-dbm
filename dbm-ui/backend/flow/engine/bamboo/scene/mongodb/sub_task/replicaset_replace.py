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
from backend.flow.consts import MongoDBClusterRole, MongoDBInstanceType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import install_plugin
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import add_install_dbmon
from backend.flow.engine.bamboo.scene.mongodb.sub_task.multi_instance_deinstall import multi_instance_deinstall
from backend.flow.plugins.components.collections.mongodb.deferred_deinstall_ticket import (
    ExecDeferredDeInstallTicketOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.mongodb_cmr_4_meta import CMRMongoDBMetaComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository

from .mongod_replace import CUTOVER_REPLACE_WITH_SOURCE_DOWN, mongod_replace


def _build_deferred_deinstall_infos(info: dict, old_instances: list, instance_type: str) -> list:
    """组装延迟下架 infos，补齐 cluster_id / role。"""
    cluster_id = None
    for inst in info.get("instances") or []:
        if inst.get("cluster_id"):
            cluster_id = inst["cluster_id"]
            break
    infos = []
    for old in old_instances:
        item = {
            "ip": old["ip"],
            "port": old["port"],
            "bk_cloud_id": old["bk_cloud_id"],
            "role": instance_type,
            "instance_type": instance_type,
            "set_id": old.get("set_id") or "",
        }
        if cluster_id:
            item["cluster_id"] = cluster_id
        infos.append(item)
    return infos


def _fill_instance_roles_from_meta(info: dict, cluster_role: str) -> list:
    """
    down=True 时不探活 primary（故障机可能不可达），仅从 meta 填 instance_role / role_status。
    sourceDown 切主不依赖 primary_ip。
    """
    instances = list(info.get("instances") or [])
    for instance in instances:
        cluster_id = instance["cluster_id"]
        cluster_info = MongoRepository().fetch_one_cluster(with_domain=False, id=cluster_id)
        ip = info["ip"]
        members = []
        if not cluster_role:
            members = cluster_info.get_shards()[0].members
        elif cluster_role == MongoDBClusterRole.ConfigSvr.value:
            members = cluster_info.get_config().members
        elif cluster_role == MongoDBClusterRole.ShardSvr.value:
            seg_range = instance.get("seg_range")
            for shard in cluster_info.get_shards():
                if shard.set_name == seg_range:
                    members = shard.members
                    break
        instance["role_status"] = "secondary"
        for member in members:
            if member.ip == ip:
                instance["instance_role"] = member.role
                break
        instance.setdefault("instance_role", "")
    return instances


def replicaset_replace(
    root_id: str, ticket_data: Optional[Dict], sub_kwargs: ActKwargs, info: dict, cluster_role: str
) -> SubBuilder:
    """
    replicaset 替换流程
    info 表示replicaset信息
    """

    # 获取变量
    sub_get_kwargs = deepcopy(sub_kwargs)

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    if not cluster_role:
        # 获取替换信息 info["mongodb"]是list
        info = info["mongodb"][0]

        # 获取信息
        sub_get_kwargs.get_host_replace(mongodb_type=ClusterType.MongoReplicaSet.value, info=info)

        # 安装蓝鲸插件
        install_plugin(pipeline=sub_pipeline, get_kwargs=sub_get_kwargs, new_cluster=False)

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

    # 根据计算容量新的 cachesize 和 oplogsize  self.replicaset_info["cacheSizeGB"]  self.replicaset_info["oplogSizeMB"]
    sub_get_kwargs.calc_param_migrate(info=info["target"], instance_num=len(info["instances"]))

    # 获取节点 role：死机走 meta，活机探 primary
    if info.get("down"):
        info["instances"] = _fill_instance_roles_from_meta(info=info, cluster_role=cluster_role)
        cutover_mode = CUTOVER_REPLACE_WITH_SOURCE_DOWN
    else:
        info["instances"] = sub_get_kwargs.get_role_replace_kwargs(info=info, cluster_role=cluster_role)
        cutover_mode = None

    # 进行替换——并行 以ip为维度
    sub_sub_pipelines = []
    for mongodb_instance in info["instances"]:
        sub_get_kwargs.db_instance = mongodb_instance
        sub_sub_pipeline = mongod_replace(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_sub_kwargs=sub_get_kwargs,
            cluster_role=cluster_role,
            info=info,
            mongod_scale=False,
            cutover_mode=cutover_mode,
        )
        sub_sub_pipelines.append(sub_sub_pipeline)
    sub_pipeline.add_parallel_sub_pipeline(sub_sub_pipelines)

    # 修改db_meta数据
    info["created_by"] = sub_get_kwargs.payload.get("created_by")
    info["bk_biz_id"] = sub_get_kwargs.payload.get("bk_biz_id")
    if not cluster_role:
        info["db_type"] = "replicaset_mongodb"
        name = "replicaset"
        for mongodb_instance in info["instances"]:
            kwargs = sub_get_kwargs.get_change_meta_replace_kwargs(info=info, instance=mongodb_instance)
            sub_pipeline.add_act(
                act_name=_("MongoDB-mongod修改meta-port:{}".format(str(mongodb_instance["port"]))),
                act_component_code=CMRMongoDBMetaComponent.code,
                kwargs=kwargs,
            )
    else:
        if cluster_role == MongoDBClusterRole.ShardSvr.value:
            info["db_type"] = "cluster_mongodb"
            name = "shard"

        elif cluster_role == MongoDBClusterRole.ConfigSvr.value:
            info["db_type"] = "mongo_config"
            name = "configDB"
        kwargs = sub_get_kwargs.get_change_meta_replace_kwargs(info=info, instance={})
        sub_pipeline.add_act(
            act_name=_("MongoDB-mongod修改meta"), act_component_code=CMRMongoDBMetaComponent.code, kwargs=kwargs
        )
    if not cluster_role:
        # 安装dbmon 副本集
        ip_list = sub_get_kwargs.payload["plugin_hosts"]
        exec_ips = [host["ip"] for host in ip_list]
        add_install_dbmon(
            root_id=root_id,
            flow_data=ticket_data,
            pipeline=sub_pipeline,
            iplist=exec_ips,
            bk_cloud_id=ip_list[0]["bk_cloud_id"],
            allow_empty_instance=True,
        )

        # 下架：故障机 down=True 出延迟下架单；否则内联卸载
        old_hosts, old_instances = sub_get_kwargs.get_old_host_replace(
            info=info, cluster_type=ClusterType.MongoReplicaSet.value
        )
        if info.get("down"):
            defer_infos = _build_deferred_deinstall_infos(
                info=info, old_instances=old_instances, instance_type=MongoDBInstanceType.MongoD.value
            )
            kwargs = {
                "infos": defer_infos,
                "creator": sub_get_kwargs.payload["created_by"],
                "bk_biz_id": sub_get_kwargs.payload["bk_biz_id"],
                "parent_ticket_id": ticket_data.get("uid"),
            }
            sub_pipeline.add_act(
                act_name=_("MongoDB-延迟下架单据"),
                act_component_code=ExecDeferredDeInstallTicketOperationComponent.code,
                kwargs=kwargs,
            )
        else:
            sub_sub_pipeline = multi_instance_deinstall(
                root_id=root_id,
                ticket_data=ticket_data,
                sub_kwargs=sub_get_kwargs,
                old_hosts=old_hosts,
                old_instances=old_instances,
                instance_type=MongoDBInstanceType.MongoD.value,
            )
            sub_pipeline.add_sub_pipeline(sub_flow=sub_sub_pipeline)

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--{}整机替换--ip:{}".format(name, info["ip"])))
