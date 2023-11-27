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
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_REDIS_START_PORT
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisBatchInstallAtomJob, RedisBatchShutdownAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

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
    cluster_kwargs = deepcopy(act_kwargs)
    if cluster_kwargs.cluster["cluster_type"] != ClusterType.TendisPredixyTendisplusCluster.value:
        raise NotImplementedError("Not supported cluster type: %s" % cluster_kwargs.cluster["cluster_type"])
    if not info["is_delete_node"]:
        raise NotImplementedError("is_delete_node is not True")
    # 校验传入的当前组数是否和元数据获取组数一致
    if info["current_group_num"] != len(cluster_kwargs.cluster["master_slave_map"]):
        raise Exception(
            _(
                "传入原机器组数: {} != 从元数据获取的机器组数: {} ,pelase check!".format(
                    info["current_group_num"], len(cluster_kwargs.cluster["master_slave_map"])
                )
            )
        )
    # 获取缩容组数，确保输入合法
    contraction_group = info["current_group_num"] - info["target_group_num"]
    if contraction_group < 1:
        raise Exception(_("缩容组数: {}小于1 ,pelase check!".format(contraction_group)))
    # 获取缩容实例（master）
    contraction_instance = []
    for ip in cluster_kwargs.cluster["master_ip"][:contraction_group]:
        for instance in cluster_kwargs.cluster["redis_master"]:
            if ip in instance:
                contraction_instance.append(instance)
                continue
    logger.info(_("+===+++++===缩容节点 contraction_instance: {} +++++===++++ ".format(contraction_instance)))
    # 待下架的ip_ports
    shutdown_ip_ports = {}
    for instance in contraction_instance:
        if instance in cluster_kwargs.cluster["ins_pair_map"]:
            ip, port = instance.split(":")
            if ip not in shutdown_ip_ports:
                shutdown_ip_ports[ip] = []
            shutdown_ip_ports[ip].append(int(port))
            # 获取缩容master对应的slave
            slave_instance = cluster_kwargs.cluster["ins_pair_map"][instance]
            slave_ip, slave_port = slave_instance.split(":")
            if slave_ip not in shutdown_ip_ports:
                shutdown_ip_ports[slave_ip] = []
            shutdown_ip_ports[slave_ip].append(int(slave_port))
    logger.info(_("+===+++++===下架实例shutdown_ip_ports: {} +++++===++++ ".format(shutdown_ip_ports)))

    # 获取第一个master机器的地址
    src_first_machine = next(iter(cluster_kwargs.cluster["master_ports"]))
    src_first_port = cluster_kwargs.cluster["master_ports"][src_first_machine][0]

    # ###集群node slots migrate for del node#################################################################
    # 迁移多个实例也是可以的，原子任务中一个master会生成一个迁移任务，并发度和迁移任务一样,并且会forget节点
    contraction_kwargs = deepcopy(cluster_kwargs)
    # 获取第一个dst_master_ip和对应的第一个dst_master_port
    dst_first_master_ip, dst_first_master_port = contraction_instance[0].split(IP_PORT_DIVIDER)

    # 下发actuator包
    trans_files = GetFileList(db_type=DBType.Redis)
    contraction_kwargs.file_list = trans_files.redis_dbmon()
    contraction_kwargs.exec_ip = dst_first_master_ip
    sub_pipeline.add_act(
        act_name=_("Redis-{}-下发工具包".format(dst_first_master_ip)),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(contraction_kwargs),
    )

    contraction_kwargs.exec_ip = src_first_machine
    contraction_kwargs.cluster["src_node"] = {
        "ip": src_first_machine,
        "port": int(src_first_port),
        "password": contraction_kwargs.cluster["password"],
    }
    contraction_kwargs.cluster["dst_node"] = {
        "ip": dst_first_master_ip,
        "port": int(dst_first_master_port),
        "password": contraction_kwargs.cluster["password"],
    }
    contraction_kwargs.cluster["to_be_del_nodes_addr"] = contraction_instance

    contraction_kwargs.get_redis_payload_func = RedisActPayload.redis_slots_migrate_4_contraction.__name__
    sub_pipeline.add_act(
        act_name=_("集群迁移slots缩容-{}".format(act_kwargs.cluster["immute_domain"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(contraction_kwargs),
    )
    # ###集群node slots migrate for del node完###############################################################

    # predixy类型的集群需要刷新配置文件 #################################################################
    predixy_kwargs = deepcopy(cluster_kwargs)
    acts_lists = []
    cluster = Cluster.objects.get(
        id=predixy_kwargs.cluster["cluster_id"], bk_biz_id=predixy_kwargs.cluster["bk_biz_id"]
    )
    # 获取所有proxy ip
    predixy_kwargs.cluster["proxy_ips"] = [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()]
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
        predixy_kwargs.exec_ip = predixy_kwargs.cluster["proxy_ips"]
        # 已下架的节点，需要在proxy里去掉
        for instance in contraction_instance:
            predixy_kwargs.cluster[
                "shell_command"
            ] = """
            cnf="$REDIS_DATA_DIR/predixy/{}/predixy.conf"
            echo "`date "+%F %T"` : before sed config $cnf: : `cat $cnf |grep  "+"|grep ":"`"
            echo "`date "+%F %T"` : exec sed -i {}"
            sed -i '/{}/d'  $cnf
            echo "`date "+%F %T"` : after sed configs : `cat $cnf |grep "+"|grep ":"`"
            """.format(
                predixy_kwargs.cluster["proxy_port"], instance, instance
            )
            acts_lists.append(
                {
                    "act_name": _("刷新Predixy本地配置--{}".format(predixy_kwargs.cluster["proxy_ips"])),
                    "act_component_code": ExecuteShellScriptComponent.code,
                    "kwargs": asdict(predixy_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_lists)
    # predixy类型的集群需要刷新配置文件 ######################################################## 完毕 ###

    # #### 下架旧redis实例和清理元数据##########################################################################
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
    # #### 下架旧实例 ###################################################################### 完毕 ###

    # 写入slots 迁移缩容记录 ############################################################
    record_kwargs = deepcopy(cluster_kwargs)
    record_kwargs.cluster = {
        # 记录元数据
        "bk_cloud_id": act_kwargs.cluster["bk_cloud_id"],
        "cluster_type": act_kwargs.cluster["cluster_type"],
        "cluster_id": act_kwargs.cluster["cluster_id"],
        "cluster_name": act_kwargs.cluster["cluster_name"],
        "status": MigrateStatus.COMPLETED,
        "old_instance_pair": act_kwargs.cluster["ins_pair_map"],
        "current_group_num": info["current_group_num"],
        "target_group_num": info["target_group_num"],
        "shutdown_master_slave_pair": shutdown_ip_ports,
        "meta_func_name": RedisDBMeta.redis_migrate_4_contraction.__name__,
    }
    sub_pipeline.add_act(
        act_name=_("写入slots 迁移缩容记录数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(record_kwargs)
    )

    return sub_pipeline.build_sub_process(
        sub_name=_("迁移slots缩容{}".format(contraction_kwargs.cluster["immute_domain"]))
    )


def redis_rebalance_slots_4_expansion(root_id: str, flow_data: dict, act_kwargs: ActKwargs, info: Dict) -> SubBuilder:
    """
    ## redis slots migrate :tendisplus rebalance slots 方式扩容
    @param root_id: flow 流程root_id
    @param flow_data: 流程参数
    @param  act_kwargs：定义活动节点的私有变量dataclass类
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
    cluster_kwargs = deepcopy(act_kwargs)
    if cluster_kwargs.cluster["cluster_type"] != ClusterType.TendisPredixyTendisplusCluster.value:
        raise NotImplementedError("Not supported cluster type: %s" % cluster_kwargs.cluster["cluster_type"])

    if info["current_group_num"] != len(cluster_kwargs.cluster["master_slave_map"]):
        raise Exception(
            _(
                "传入原机器组数: {} != 从元数据获取的机器组数: {} ,pelase check!".format(
                    info["current_group_num"], len(cluster_kwargs.cluster["master_slave_map"])
                )
            )
        )

    scale_up_group = info["target_group_num"] - info["current_group_num"]
    if len(info["new_ip_group"]) != scale_up_group:
        raise Exception(
            _("传入新增机器组数: {} != 扩容新增机器组数: {} ,pelase check!".format(len(info["new_ip_group"]), scale_up_group))
        )

    # 获取第一个master机器的地址,来获取单台集群部署的节点数，新机器部署一样的节点数，保持一致
    src_first_machine = next(iter(cluster_kwargs.cluster["master_ports"]))
    src_first_port = cluster_kwargs.cluster["master_ports"][src_first_machine][0]
    instance_numb = len(cluster_kwargs.cluster["master_ports"][src_first_machine])

    # ### 部署redis #############################################################################
    sub_pipelines_install = []
    # 部署端口信息，每台机器都一样
    new_ports = []
    for inst_no in range(0, instance_numb):
        new_ports.append(DEFAULT_REDIS_START_PORT + inst_no)
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
    # ### 部署redis完成 #############################################################################

    # ###建立集群关系和做主从#################################################################################
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
    # ###建立集群关系和做主从#################################################################################

    # ###集群reblance 迁移slots扩容###########################################################################

    reblance_kwargs = deepcopy(act_kwargs)
    # 获取第一个dst_master_ip和对应的第一个dst_master_port
    dst_first_master_ip = new_ins_pair_map[0]["master_ip"]
    dst_first_master_port = new_ins_pair_map[0]["master_port"]
    reblance_kwargs.exec_ip = dst_first_master_ip

    reblance_kwargs.cluster["src_node"] = {
        "ip": src_first_machine,
        "port": src_first_port,
        "password": reblance_kwargs.cluster["password"],
    }
    reblance_kwargs.cluster["dst_node"] = {
        "ip": dst_first_master_ip,
        "port": dst_first_master_port,
        "password": reblance_kwargs.cluster["password"],
    }
    reblance_kwargs.get_redis_payload_func = RedisActPayload.redis_slots_migrate_4_expansion.__name__
    sub_pipeline.add_act(
        act_name=_("集群reblance扩容-{}".format(act_kwargs.cluster["immute_domain"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(reblance_kwargs),
    )
    # ###集群reblance完####################################################################################

    # ###元数据加入集群开始####################################################################################

    dbmeta_kwargs = deepcopy(act_kwargs)
    # 节点信息加入到集群，使的可以获取到集群的配置 （DBHA 可以提前监控）
    dbmeta_kwargs.cluster["sync_relation"] = []
    for ins_pair_map in new_ins_pair_map:
        dbmeta_kwargs.cluster["sync_relation"].append(
            {
                "old_ejector": {  # not important , but must have.
                    "ip": src_first_machine,
                    "port": src_first_port,
                },
                "ejector": {
                    "ip": ins_pair_map["master_ip"],
                    "port": ins_pair_map["master_port"],
                },
                "receiver": {
                    "ip": ins_pair_map["slave_ip"],
                    "port": ins_pair_map["slave_port"],
                },
            }
        )
    logger.info(_("======新增元数据[sync_relation]关系: {} +++++++++ ".format(dbmeta_kwargs.cluster["sync_relation"])))
    dbmeta_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_replace_pair.__name__
    sub_pipeline.add_act(
        act_name=_("Redis-元数据加入集群"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(dbmeta_kwargs)
    )
    # ###元数据加入集群完成####################################################################################

    # predixy类型的集群需要刷新配置文件 #################################################################
    predixy_kwargs = deepcopy(act_kwargs)
    acts_lists = []
    cluster = Cluster.objects.get(
        id=predixy_kwargs.cluster["cluster_id"], bk_biz_id=predixy_kwargs.cluster["bk_biz_id"]
    )
    # 获取所有proxy ip
    predixy_kwargs.cluster["proxy_ips"] = [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()]
    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
        predixy_kwargs.exec_ip = predixy_kwargs.cluster["proxy_ips"]
        for instance in new_master_instance:
            predixy_kwargs.cluster[
                "shell_command"
            ] = """
            cnf="$REDIS_DATA_DIR/predixy/{}/predixy.conf"
            echo "`date "+%F %T"` : before sed config $cnf: : `cat $cnf |grep  "+"|grep ":"`"
            echo "`date "+%F %T"` : exec sed -i /Servers {{/a\\    + {}"
            sed -i '/Servers {{/a\\    + {}'  $cnf
            echo "`date "+%F %T"` : after sed configs : `cat $cnf |grep "+"|grep ":"`"
            """.format(
                predixy_kwargs.cluster["proxy_port"], instance, instance
            )
            acts_lists.append(
                {
                    "act_name": _("刷新Predixy本地配置--{}".format(predixy_kwargs.cluster["proxy_ips"])),
                    "act_component_code": ExecuteShellScriptComponent.code,
                    "kwargs": asdict(predixy_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=acts_lists)
    # predixy类型的集群需要刷新配置文件 ######################################################## 完毕 ###

    # 写入slots 迁移扩容记录 ############################################################
    record_kwargs = deepcopy(act_kwargs)
    record_kwargs.cluster = {
        # 记录元数据
        "bk_cloud_id": act_kwargs.cluster["bk_cloud_id"],
        "cluster_type": act_kwargs.cluster["cluster_type"],
        "cluster_id": act_kwargs.cluster["cluster_id"],
        "cluster_name": act_kwargs.cluster["cluster_name"],
        "status": MigrateStatus.COMPLETED,
        "old_instance_pair": act_kwargs.cluster["ins_pair_map"],
        "current_group_num": info["current_group_num"],
        "target_group_num": info["target_group_num"],
        "new_ip_group": info["new_ip_group"],
        "specification": info["resource_spec"],
        "add_new_master_slave_pair": new_ins_pair_map,
        "meta_func_name": RedisDBMeta.redis_rebalance_4_expansion.__name__,
    }
    sub_pipeline.add_act(
        act_name=_("写入slots 迁移扩容记录数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(record_kwargs)
    )

    return sub_pipeline.build_sub_process(sub_name=_("迁移slots扩容{}".format(predixy_kwargs.cluster["immute_domain"])))
