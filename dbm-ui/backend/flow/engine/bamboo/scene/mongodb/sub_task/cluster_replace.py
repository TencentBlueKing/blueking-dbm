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
from backend.flow.engine.bamboo.scene.common.builder import Conditions, SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import install_plugin
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import add_install_dbmon
from backend.flow.engine.bamboo.scene.mongodb.sub_task.multi_instance_deinstall import multi_instance_deinstall
from backend.flow.plugins.components.collections.mongodb.deferred_deinstall_ticket import (
    ExecDeferredDeInstallTicketOperationComponent,
)
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job import ExecuteDBActuatorJobComponent
from backend.flow.plugins.components.collections.mongodb.mongo_replace_probe_down import MongoReplaceProbeDownComponent
from backend.flow.plugins.components.collections.mongodb.mongodb_cmr_4_meta import CMRMongoDBMetaComponent
from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

from .mongos_replace import mongos_replace
from .replicaset_replace import _build_deferred_deinstall_infos, replicaset_replace


def _cluster_instances_for_deferred(info: dict) -> list:
    """从分片替换 info 收集实例，供延迟下架补 cluster_id。"""
    instances = []
    for role_key in ("mongodb", "mongo_config", "mongos"):
        for host in info.get(role_key) or []:
            instances.extend(host.get("instances") or [])
    return instances


def _deferred_deinstall_act(pipeline, sub_get_kwargs, info, ticket_data, instance_type, old_instances, extend=True):
    defer_infos = _build_deferred_deinstall_infos(
        info={"instances": _cluster_instances_for_deferred(info)},
        old_instances=old_instances,
        instance_type=instance_type,
    )
    kwargs = {
        "infos": defer_infos,
        "creator": sub_get_kwargs.payload["created_by"],
        "bk_biz_id": sub_get_kwargs.payload["bk_biz_id"],
        "parent_ticket_id": ticket_data.get("uid") if ticket_data else None,
    }
    return pipeline.add_act(
        act_name=_("MongoDB-延迟下架单据"),
        act_component_code=ExecDeferredDeInstallTicketOperationComponent.code,
        kwargs=kwargs,
        extend=extend,
    )


def _build_mongos_finish_sub(
    root_id: str,
    ticket_data: Optional[Dict],
    sub_get_kwargs: ActKwargs,
    mongos_info_by_ip: dict,
    down: bool,
):
    finish_sub = SubBuilder(root_id=root_id, data=ticket_data)
    cmr_info = {
        "db_type": "mongos",
        "created_by": sub_get_kwargs.payload.get("created_by"),
        "bk_biz_id": sub_get_kwargs.payload.get("bk_biz_id"),
        "mongos": [mongos_info_by_ip],
        "down": down,
    }
    cmr_kwargs = sub_get_kwargs.get_change_meta_replace_kwargs(info=cmr_info, instance={})
    finish_sub.add_act(
        act_name=_("MongoDB-mongos修改meta-{}".format(mongos_info_by_ip["ip"])),
        act_component_code=CMRMongoDBMetaComponent.code,
        kwargs=cmr_kwargs,
    )
    old_hosts = [{"ip": mongos_info_by_ip["ip"], "bk_cloud_id": mongos_info_by_ip["bk_cloud_id"]}]
    old_instances = [
        {
            "ip": mongos_info_by_ip["ip"],
            "bk_cloud_id": mongos_info_by_ip["bk_cloud_id"],
            "port": instance["port"],
            "set_id": instance["cluster_name"],
        }
        for instance in mongos_info_by_ip.get("instances") or []
    ]
    if down:
        _deferred_deinstall_act(
            finish_sub,
            sub_get_kwargs,
            {"mongos": [mongos_info_by_ip]},
            ticket_data,
            MongoDBInstanceType.MongoS.value,
            old_instances,
        )
    else:
        finish_sub.add_sub_pipeline(
            sub_flow=multi_instance_deinstall(
                root_id=root_id,
                ticket_data=ticket_data,
                sub_kwargs=sub_get_kwargs,
                old_hosts=old_hosts,
                old_instances=old_instances,
                instance_type=MongoDBInstanceType.MongoS.value,
            )
        )
    return finish_sub.build_sub_process(sub_name=_("MongoDB-mongos元数据与下架-{}".format(mongos_info_by_ip["ip"])))


def _append_mongos_cmr_and_deinstall(root_id, ticket_data, sub_pipeline, sub_get_kwargs, info):
    for mongos_info_by_ip in info.get("mongos") or []:
        if info.get("down") or mongos_info_by_ip.get("down"):
            sub_pipeline.add_sub_pipeline(
                sub_flow=_build_mongos_finish_sub(
                    root_id=root_id,
                    ticket_data=ticket_data,
                    sub_get_kwargs=sub_get_kwargs,
                    mongos_info_by_ip=mongos_info_by_ip,
                    down=True,
                )
            )
            continue

        probe_act = sub_pipeline.add_act(
            act_name=_("MongoDB-探测故障机下架方式-{}".format(mongos_info_by_ip["ip"])),
            act_component_code=MongoReplaceProbeDownComponent.code,
            kwargs={"ip": mongos_info_by_ip["ip"], "bk_cloud_id": mongos_info_by_ip.get("bk_cloud_id") or 0},
            extend=False,
        )
        down_branch = _build_mongos_finish_sub(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_get_kwargs=sub_get_kwargs,
            mongos_info_by_ip=mongos_info_by_ip,
            down=True,
        )
        live_branch = _build_mongos_finish_sub(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_get_kwargs=sub_get_kwargs,
            mongos_info_by_ip=mongos_info_by_ip,
            down=False,
        )
        sub_pipeline.add_conditional_subs(
            source_act=probe_act,
            conditions=[
                Conditions(act_object=down_branch, express="==1"),
                Conditions(act_object=live_branch, express="==0"),
            ],
            name=_("判断是否延迟下架"),
            conditions_param="replace_down",
        )


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
    if info.get("mongo_config"):
        sub_get_kwargs.get_cluster_info_deinstall(cluster_id=info["mongo_config"][0]["instances"][0]["cluster_id"])
        config_port = info["mongo_config"][0]["instances"][0]["port"]
        old_config_node = "{}:{}".format(info["mongo_config"][0]["ip"], config_port)
        new_config_node = "{}:{}".format(info["mongo_config"][0]["target"]["ip"], config_port)
        mongos_nodes = sub_get_kwargs.payload["mongos_nodes"]

    # 创建子流程
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    # 获取信息
    sub_get_kwargs.get_host_replace(mongodb_type=ClusterType.MongoShardedCluster.value, info=info)
    # 下发介质获取mongos
    if info.get("mongo_config"):
        sub_get_kwargs.get_mongos_host_replace()

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

    # 进行shard和config替换——并行
    sub_sub_pipelines = []
    # 替换config 以ip为维度
    if info.get("mongo_config"):
        for config_info_by_ip in info.get("mongo_config"):
            sub_sub_pipeline = replicaset_replace(
                root_id=root_id,
                ticket_data=ticket_data,
                sub_kwargs=sub_get_kwargs,
                info=config_info_by_ip,
                cluster_role=MongoDBClusterRole.ConfigSvr.value,
            )
            sub_sub_pipelines.append(sub_sub_pipeline)
    # 替换shard 以ip为维度
    if info.get("mongodb"):
        for shard_info_by_ip in info.get("mongodb"):
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
    if info.get("mongo_config"):
        act_lists = []
        for mongos_node in mongos_nodes:
            mongos_node["role"] = MongoDBInstanceType.MongoS.value
            kwargs = sub_get_kwargs.get_instance_restart_kwargs(
                host=mongos_node,
                cache_size_gb=0,
                mongos_conf_db_old=old_config_node,
                mongos_conf_db_new=new_config_node,
                cluster_id=info.get("mongo_config")[0]["instances"][0]["cluster_id"],
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
    if info.get("mongos"):
        sub_sub_pipelines = []
        for mongos_info_by_ip in info.get("mongos"):
            for mongos_instance in mongos_info_by_ip["instances"]:
                sub_get_kwargs.db_instance = mongos_instance
                sub_sub_pipeline = mongos_replace(
                    root_id=root_id, ticket_data=ticket_data, sub_sub_kwargs=sub_get_kwargs, info=mongos_info_by_ip
                )
                sub_sub_pipelines.append(sub_sub_pipeline)
        sub_pipeline.add_parallel_sub_pipeline(sub_sub_pipelines)
        # mongos 按单机探测结果决定 CMR 是否保留 Machine 及走延迟/内联下架
        _append_mongos_cmr_and_deinstall(
            root_id=root_id,
            ticket_data=ticket_data,
            sub_pipeline=sub_pipeline,
            sub_get_kwargs=sub_get_kwargs,
            info=info,
        )
    # 安装dbmon（mongodb / mongo_config 的旧机下架已在各自 replicaset_replace 分支内完成）
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

    return sub_pipeline.build_sub_process(sub_name=_("MongoDB--cluster整机替换"))
