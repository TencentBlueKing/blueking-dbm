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

import logging.config
from copy import deepcopy
from dataclasses import asdict
from typing import Dict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole, MigrateStatus
from backend.flow.consts import DEFAULT_REDIS_START_PORT
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    ClusterPredixyConfigServersRewriteAtomJob,
    RedisBatchInstallAtomJob,
    RedisBatchShutdownAtomJob,
)
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cluster_info_by_cluster_id

logger = logging.getLogger("flow")


# redis slots migrate :tendisplus 迁移特定slots
def redis_specifed_slots_migrate(root_id: str, flow_data: dict, act_kwargs: ActKwargs, info: Dict) -> SubBuilder:
    """
    @param root_id: flow 流程root_id
    @param flow_data: 流程参数
    @param  act_kwargs：定义活动节点的私有变量dataclass类
    @param info: 单据单个migrate_info信息
    slots 迁移：将特定slots从 src_node节点 迁移到dst_node，这样slots的keys也迁移到dst_node了
    直接调度迁移actuator  -> 写入扩缩容表

    """

    sub_pipeline = SubBuilder(root_id=root_id, data=flow_data)
    specified_slots_kwargs = deepcopy(act_kwargs)
    if specified_slots_kwargs.cluster["cluster_type"] != ClusterType.TendisPredixyTendisplusCluster.value:
        raise NotImplementedError("Not supported cluster type: %s" % specified_slots_kwargs.cluster["cluster_type"])
    # 判断是否是迁移特定的slots
    if info["slots"] is not None:
        master_instance = specified_slots_kwargs.cluster["redis_master"]
        # 判断是否是主节点
        if info["src_node"] in master_instance and info["dst_node"] in master_instance:
            specified_slots_kwargs.cluster["slots"] = info["slots"]
            src_ip, src_port = info["src_node"].split(":")
            dst_ip, dst_port = info["dst_node"].split(":")

            # 下发actuator包 ##############################################################
            trans_files = GetFileList(db_type=DBType.Redis)
            specified_slots_kwargs.file_list = trans_files.redis_dbmon()
            specified_slots_kwargs.exec_ip = src_ip
            sub_pipeline.add_act(
                act_name=_("Redis-{}-下发工具包".format(src_ip)),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(specified_slots_kwargs),
            )
            # 下发actuator包完成 ###########################################################

            # slots 迁移 ##################################################################
            specified_slots_kwargs.cluster["src_node"] = {
                "ip": src_ip,
                "port": int(src_port),
                "password": specified_slots_kwargs.cluster["password"],
            }
            specified_slots_kwargs.cluster["dst_node"] = {
                "ip": dst_ip,
                "port": int(dst_port),
                "password": specified_slots_kwargs.cluster["password"],
            }
            specified_slots_kwargs.get_redis_payload_func = RedisActPayload.redis_slots_migrate_4_hotkey.__name__
            sub_pipeline.add_act(
                act_name=_("迁移特定slots子任务-{}".format(specified_slots_kwargs.cluster["immute_domain"])),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(specified_slots_kwargs),
            )

            # slots 迁移完成 ################################################################

            # 写入slots 迁移记录 ############################################################
            record_kwargs = deepcopy(specified_slots_kwargs)
            record_kwargs.cluster = {
                # 记录元数据
                "bk_cloud_id": specified_slots_kwargs.cluster["bk_cloud_id"],
                "cluster_type": specified_slots_kwargs.cluster["cluster_type"],
                "cluster_id": specified_slots_kwargs.cluster["cluster_id"],
                "cluster_name": specified_slots_kwargs.cluster["cluster_name"],
                "status": MigrateStatus.COMPLETED,
                "migrate_specified_slot": info,
                "meta_func_name": RedisDBMeta.specifed_slots_migrate_record.__name__,
            }
            sub_pipeline.add_act(
                act_name=_("写入slots 迁移记录数据"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(record_kwargs),
            )

    return sub_pipeline.build_sub_process(
        sub_name=_("迁移slots{}".format(specified_slots_kwargs.cluster["immute_domain"]))
    )


# redis slots migrate :tendisplus migrate slots 方式缩容
def redis_migrate_slots_4_contraction(root_id: str, flow_data: dict, act_kwargs: ActKwargs, info: Dict) -> SubBuilder:
    """
     @param root_id: flow 流程root_id
     @param flow_data: 流程参数
     @param  act_kwargs：定义活动节点的私有变量dataclass类
     @param info: 单据info信息
     缩容:
     根据传入的节点数得到待删除的instance -> slots 迁移 -> predixy 配置刷新(去掉缩容的节点) -> 节点下架&删除元数据
     -> 写入扩缩容表

    {
         "bk_biz_id": 3,
         "uid": "2022051612120001",
         "created_by":"admin",
         "ticket_type":"REDIS_SLOTS_MIGRATE",
         "infos": [
             {
             "cluster_id": 12,
             "bk_cloud_id": 0,
             "is_delete_node":true,
             "current_group_num": 2,
             "target_group_num": 1
             }
         ]
     }

    """
    sub_pipeline = SubBuilder(root_id=root_id, data=flow_data)
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs = ActKwargs()
    act_kwargs.set_trans_data_dataclass = CommonContext.__name__
    act_kwargs.file_list = trans_files.redis_base()
    act_kwargs.is_update_trans_data = True
    cluster_info = get_cluster_info_by_cluster_id(cluster_id=info["cluster_id"])
    act_kwargs.cluster.update(cluster_info)
    act_kwargs.cluster["db_version"] = cluster_info["major_version"]
    act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )

    cluster_kwargs = deepcopy(act_kwargs)
    if cluster_kwargs.cluster["cluster_type"] != ClusterType.TendisPredixyTendisplusCluster.value:
        raise NotImplementedError("Not supported cluster type: %s" % cluster_kwargs.cluster["cluster_type"])
    if not info["is_delete_node"]:
        raise NotImplementedError("is_delete_node is not True")
    # 获取缩容组数，确保输入合法
    contraction_group = info["current_group_num"] - info["target_group_num"]
    if contraction_group < 1:
        raise Exception(_("缩容组数: {}小于1 ,pelase check!".format(contraction_group)))
    # 获取缩容实例（master)
    to_shutdown_master_inst = []
    to_shutdown_master_ips = set()
    for ip in cluster_info["master_ips"][:contraction_group]:
        to_shutdown_master_ips.add(ip)
        for port in cluster_info["master_ports"][ip]:
            to_shutdown_master_inst.append(f"{ip}:{port}")
    logger.info(_("+===+++++===缩容节点 contraction_instance: {} +++++===++++ ".format(to_shutdown_master_inst)))
    # 待下架的ip_ports
    shutdown_ip_ports = {}
    for master_ip in to_shutdown_master_ips:
        shutdown_ip_ports[master_ip] = cluster_info["master_ports"][master_ip]
        slave_ip = cluster_info["master_ip_to_slave_ip"][master_ip]
        shutdown_ip_ports[slave_ip] = cluster_info["slave_ports"][slave_ip]
    logger.info(_("+===+++++===下架实例shutdown_ip_ports: {} +++++===++++ ".format(shutdown_ip_ports)))

    # 获取第一个master机器的地址
    src_first_machine = cluster_info["master_ips"][0]
    src_first_port = cluster_info["master_ports"][src_first_machine][0]

    # ###集群node slots migrate for del node
    # 迁移多个实例也是可以的，原子任务中一个master会生成一个迁移任务，并发度和迁移任务一样,并且会forget节点
    contraction_kwargs = deepcopy(cluster_kwargs)
    # 获取第一个dst_master_ip和对应的第一个dst_master_port
    to_shutdown_first_master_ip, to_shutdown_first_master_port = to_shutdown_master_inst[0].split(IP_PORT_DIVIDER)

    # 下发actuator包
    trans_files = GetFileList(db_type=DBType.Redis)
    contraction_kwargs.file_list = trans_files.redis_dbmon()
    contraction_kwargs.exec_ip = to_shutdown_first_master_ip
    sub_pipeline.add_act(
        act_name=_("Redis-{}-下发工具包".format(to_shutdown_first_master_ip)),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(contraction_kwargs),
    )

    contraction_kwargs.exec_ip = src_first_machine
    contraction_kwargs.cluster["src_node"] = {
        "ip": src_first_machine,
        "port": int(src_first_port),
        "password": cluster_info["redis_password"],
    }
    contraction_kwargs.cluster["dst_node"] = {
        "ip": to_shutdown_first_master_ip,
        "port": int(to_shutdown_first_master_port),
        "password": cluster_info["redis_password"],
    }
    contraction_kwargs.cluster["to_be_del_nodes_addr"] = to_shutdown_master_inst

    contraction_kwargs.get_redis_payload_func = RedisActPayload.redis_slots_migrate_4_contraction.__name__
    sub_pipeline.add_act(
        act_name=_("集群迁移slots缩容-{}".format(act_kwargs.cluster["immute_domain"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(contraction_kwargs),
    )
    # 集群node slots migrate for del node完

    # 清理集群关系
    dbmeta_kwargs = deepcopy(act_kwargs)
    dbmeta_kwargs.cluster["meta_func_name"] = RedisDBMeta.tendisplus_remove_instance_pair.__name__
    dbmeta_kwargs.cluster["params"] = {"cluster_id": info["cluster_id"], "replication_pairs": []}
    for master_ip in to_shutdown_master_ips:
        slave_ip = cluster_info["master_ip_to_slave_ip"][master_ip]
        master_ports = cluster_info["master_ports"][master_ip]
        for port in master_ports:
            dbmeta_kwargs.cluster["params"]["replication_pairs"].append(
                {
                    "master": {
                        "ip": master_ip,
                        "port": port,
                    },
                    "slave": {
                        "ip": slave_ip,
                        "port": port,
                    },
                }
            )
    sub_pipeline.add_act(
        act_name=_("集群关系清理"),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(dbmeta_kwargs),
    )
    # 清理集群关系 完毕

    # 下架旧redis实例和清理元数据
    shutdown_kwargs = deepcopy(cluster_kwargs)
    sub_pipelines = []
    for ip_address, ports in shutdown_ip_ports.items():
        params = {
            "ip": ip_address,
            "ports": ports,
        }
        sub_builder = RedisBatchShutdownAtomJob(root_id, flow_data, shutdown_kwargs, params)
        sub_pipelines.append(sub_builder)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
    # 下架旧实例

    # predixy类型的集群需要刷新配置文件
    predixy_kwargs = deepcopy(act_kwargs)
    predixy_conf_rewrite_bulider = ClusterPredixyConfigServersRewriteAtomJob(
        root_id,
        flow_data,
        predixy_kwargs,
        {"cluster_domain": cluster_info["immute_domain"], "to_remove_servers": []},
    )
    if predixy_conf_rewrite_bulider:
        sub_pipeline.add_sub_pipeline(predixy_conf_rewrite_bulider)
    # predixy类型的集群需要刷新配置文件

    # 写入slots 迁移缩容记录
    record_kwargs = deepcopy(cluster_kwargs)
    record_kwargs.cluster = {
        # 记录元数据
        "bk_cloud_id": cluster_info["bk_cloud_id"],
        "cluster_type": cluster_info["cluster_type"],
        "cluster_id": cluster_info["cluster_id"],
        "cluster_name": cluster_info["cluster_name"],
        "status": MigrateStatus.COMPLETED,
        "old_instance_pair": cluster_info["master_ins_to_slave_ins"],
        "current_group_num": info["current_group_num"],
        "target_group_num": info["target_group_num"],
        "shutdown_master_slave_pair": shutdown_ip_ports,
        "meta_func_name": RedisDBMeta.redis_migrate_4_contraction.__name__,
    }
    sub_pipeline.add_act(
        act_name=_("写入slots 迁移缩容记录数据"),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(record_kwargs),
    )

    return sub_pipeline.build_sub_process(
        sub_name=_("迁移slots缩容{}".format(contraction_kwargs.cluster["immute_domain"]))
    )


def redis_rebalance_slots_4_expansion(root_id: str, flow_data: dict, act_kwargs: ActKwargs, info: Dict) -> SubBuilder:
    """
    ## redis slots migrate :tendisplus rebalance slots 方式扩容
    @param root_id: flow 流程root_id
    @param flow_data: 流程参数
    @param  act_kwargs:定义活动节点的私有变量dataclass类
    @param info: 单据info信息
    扩容：
    部署redis -》 建立集群关系和做主从 -》 集群reblance（迁移slots扩容）-》 元数据加入集群 -》 刷新predixy配置文件
    -> 写入扩缩容表

       {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"admin",
        "ticket_type":"REDIS_SLOTS_MIGRATE",
        "infos": [
            {
            "cluster_id": 12,
            "bk_cloud_id": 0,
            "current_group_num": 1,
            "target_group_num": 2,
            "new_ip_group":[
                {
                    "master":"aa.bb.cc.dd",
                    "slave":"xx.bb.cc.dd"
                }

            ],
         "resource_spec": {
            "redis": {
                "id": 1}}
           }

        ]
    }

    """

    sub_pipeline = SubBuilder(root_id=root_id, data=flow_data)
    trans_files = GetFileList(db_type=DBType.Redis)
    act_kwargs = ActKwargs()
    act_kwargs.set_trans_data_dataclass = CommonContext.__name__
    act_kwargs.file_list = trans_files.redis_base()
    act_kwargs.is_update_trans_data = True
    cluster_info = get_cluster_info_by_cluster_id(cluster_id=info["cluster_id"])
    act_kwargs.cluster.update(cluster_info)
    act_kwargs.cluster["db_version"] = cluster_info["major_version"]
    act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
    sub_pipeline.add_act(
        act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
    )

    cluster_kwargs = deepcopy(act_kwargs)
    if cluster_kwargs.cluster["cluster_type"] != ClusterType.TendisPredixyTendisplusCluster.value:
        raise NotImplementedError("Not supported cluster type: %s" % cluster_kwargs.cluster["cluster_type"])

    # 获取第一个master机器的地址,来获取单台集群部署的节点数，新机器部署一样的节点数，保持一致
    src_first_machine = cluster_info["master_ips"][0]
    src_first_port = cluster_info["master_ports"][src_first_machine][0]
    instance_numb = len(cluster_info["master_ports"][src_first_machine])

    # ### 部署redis
    sub_pipelines_install = []
    # 部署端口信息，每台机器都一样
    new_ports = cluster_info["master_ports"][src_first_machine]
    resource_spec = info["resource_spec"]["redis"]
    for ip_group in info["new_ip_group"]:
        for ip in ip_group.values():
            sub_builder = RedisBatchInstallAtomJob(
                root_id,
                flow_data,
                cluster_kwargs,
                {
                    "ip": ip,
                    "meta_role": InstanceRole.REDIS_MASTER.value,
                    "start_port": DEFAULT_REDIS_START_PORT,
                    "ports": new_ports,
                    "instance_numb": instance_numb,
                    "spec_id": resource_spec["id"],
                    "spec_config": resource_spec,
                },
            )
            sub_pipelines_install.append(sub_builder)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines_install)
    # ### 部署redis完成

    # ###建立集群关系和做主从
    ins_meet_kwargs = deepcopy(act_kwargs)
    new_ins_pair_map = []
    new_master_instance = []
    for ip_group in info["new_ip_group"]:
        master_ip = ip_group["master"]
        slave_ip = ip_group["slave"]
        for port in new_ports:
            # 获取master 节点信息，添加到predixy.conf文件中
            new_master_instance.append("{}{}{}".format(master_ip, IP_PORT_DIVIDER, port))
            # 新部署的shard的对应关系
            new_ins_pair_map.append(
                {"master_ip": master_ip, "master_port": port, "slave_ip": slave_ip, "slave_port": port}
            )
    logger.info(_("+===+++++===新部署节点new_ins_pair_map: {} +++++===++++ ".format(new_ins_pair_map)))
    # 下发actuator,新节点加入集群建立主从，在源集群的第一个ip上执行就好
    ins_meet_kwargs.exec_ip = src_first_machine
    ins_meet_kwargs.cluster["meet_instances"] = new_ins_pair_map
    ins_meet_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_meet_4_scene.__name__
    sub_pipeline.add_act(
        act_name=_("新节点加入源集群和做主从-{}".format(act_kwargs.cluster["immute_domain"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(ins_meet_kwargs),
    )
    # ###建立集群关系和做主从

    # ###集群reblance 迁移slots扩容

    reblance_kwargs = deepcopy(act_kwargs)
    # 获取第一个dst_master_ip和对应的第一个dst_master_port
    dst_first_master_ip = new_ins_pair_map[0]["master_ip"]
    dst_first_master_port = new_ins_pair_map[0]["master_port"]
    reblance_kwargs.exec_ip = dst_first_master_ip

    reblance_kwargs.cluster["src_node"] = {
        "ip": src_first_machine,
        "port": src_first_port,
        "password": cluster_info["redis_password"],
    }
    reblance_kwargs.cluster["dst_node"] = {
        "ip": dst_first_master_ip,
        "port": dst_first_master_port,
        "password": cluster_info["redis_password"],
    }
    reblance_kwargs.get_redis_payload_func = RedisActPayload.redis_slots_migrate_4_expansion.__name__
    sub_pipeline.add_act(
        act_name=_("集群reblance扩容-{}".format(act_kwargs.cluster["immute_domain"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(reblance_kwargs),
    )
    # ###集群reblance完

    # ###元数据加入集群开始
    # 节点信息加入到集群，使的可以获取到集群的配置 （DBHA 可以提前监控）
    dbmeta_kwargs = deepcopy(act_kwargs)
    dbmeta_kwargs.cluster["meta_func_name"] = RedisDBMeta.tendisplus_add_instance_pairs.__name__
    dbmeta_kwargs.cluster["params"] = {"cluster_id": info["cluster_id"], "replication_pairs": []}
    for ip_group in info["new_ip_group"]:
        master_ip = ip_group["master"]
        slave_ip = ip_group["slave"]
        for port in new_ports:
            dbmeta_kwargs.cluster["params"]["replication_pairs"].append(
                {
                    "master": {
                        "ip": master_ip,
                        "port": port,
                    },
                    "slave": {
                        "ip": slave_ip,
                        "port": port,
                    },
                }
            )
    sub_pipeline.add_act(
        act_name=_("元数据更新"),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(cluster_kwargs),
    )
    # ###元数据加入集群完成

    # predixy类型的集群需要刷新配置文件
    predixy_kwargs = deepcopy(act_kwargs)
    predixy_conf_rewrite_bulider = ClusterPredixyConfigServersRewriteAtomJob(
        root_id,
        flow_data,
        predixy_kwargs,
        {"cluster_domain": cluster_info["immute_domain"], "to_remove_servers": []},
    )
    if predixy_conf_rewrite_bulider:
        sub_pipeline.add_sub_pipeline(predixy_conf_rewrite_bulider)

    # 写入slots 迁移扩容记录
    record_kwargs = deepcopy(act_kwargs)
    record_kwargs.cluster = {
        # 记录元数据
        "bk_cloud_id": cluster_info["bk_cloud_id"],
        "cluster_type": cluster_info["cluster_type"],
        "cluster_id": cluster_info["cluster_id"],
        "cluster_name": cluster_info["cluster_name"],
        "status": MigrateStatus.COMPLETED,
        "old_instance_pair": cluster_info["master_ins_to_slave_ins"],
        "current_group_num": info["current_group_num"],
        "target_group_num": info["target_group_num"],
        "new_ip_group": info["new_ip_group"],
        "specification": info["resource_spec"],
        "add_new_master_slave_pair": new_ins_pair_map,
        "meta_func_name": RedisDBMeta.redis_rebalance_4_expansion.__name__,
    }
    sub_pipeline.add_act(
        act_name=_("写入slots 迁移扩容记录数据"),
        act_component_code=RedisDBMetaComponent.code,
        kwargs=asdict(record_kwargs),
    )

    return sub_pipeline.build_sub_process(sub_name=_("迁移slots扩容{}".format(predixy_kwargs.cluster["immute_domain"])))
