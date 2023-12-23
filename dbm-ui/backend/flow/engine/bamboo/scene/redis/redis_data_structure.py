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
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta import api
from backend.db_meta.enums import DataStructureStatus, InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.redis.rollback.handlers import DataStructureHandler
from backend.flow.consts import DEFAULT_DB_MODULE_ID, DEFAULT_REDIS_START_PORT, ConfigTypeEnum, WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisBatchInstallAtomJob
from backend.flow.engine.bamboo.scene.redis.common.exceptions import TendisGetBinlogFailedException
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_sub import redis_backupfile_download
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_data_structure_actuator_script import (
    ExecuteDataStructureActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.redis.exec_shell_script import (
    ExecuteShellScriptComponent,
    RedisDataStructurePrecheckComponent,
)
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.psuh_data_structure_json_script import (
    PushDataStructureJsonScriptComponent,
)
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisDataStructureContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.utils.time import str2datetime

logger = logging.getLogger("flow")


class RedisDataStructureFlow(object):
    """
        ## redis 数据构造
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"admin",
        "ticket_type":"REDIS_DATA_STRUCTURE",
        "infos": [
          {
            "cluster_id": 1,
            "bk_cloud_id": 1,
            "master_instances":[
                "127.0.0.1:30000", "127.0.0.1:30002"
            ],
            "recovery_time_point": "2022-12-12 11:11:11",
            "redis": [
                {"ip": "3.3.3.1", "bk_cloud_id": 0, "bk_host_id": 2},
                {"ip": "3.3.3.2", "bk_cloud_id": 0, "bk_host_id": 2},
            ],
            "resource_spec": {
                "redis": {"id": 1}
            }
          }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def redis_data_structure_flow(self):

        redis_pipeline_all = Builder(root_id=self.root_id, data=self.data)

        # 支持批量操作
        sub_pipelines_multi_cluster = []
        for info in self.data["infos"]:
            """"""
            logger.info("redis_data_structure_flow info:{}".format(info))
            redis_pipeline, act_kwargs = self.__init_builder(_("REDIS_DATA_STRUCTURE"), info)
            # 获取 kvstorecount
            redis_config = self.__get_cluster_config(
                act_kwargs.cluster["domain_name"],
                act_kwargs.cluster["db_version"],
                ConfigTypeEnum.DBConf,
                act_kwargs.cluster["cluster_type"],
            )

            if act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
                logger.info("redis_data_structure_flow kvstorecount:{}".format(redis_config["kvstorecount"]))
                act_kwargs.cluster["kvstorecount"] = redis_config["kvstorecount"]
            act_kwargs.cluster["ticket_type"] = self.data["ticket_type"]

            cluster_kwargs = deepcopy(act_kwargs)
            # 源节点列表
            logger.info("redis_data_structure_flow  info['master_instances']: {}".format(info["master_instances"]))
            # sass 层传入节点信息（集群维度传入所有节点）
            # 根据传入的master_instance 获取其slave_instance
            cluster_src_instance = self.get_slave_instance_by_master(info["master_instances"], cluster_kwargs)

            logger.info("redis_data_structure_flow cluster_src_instance: {}".format(cluster_src_instance))
            logger.info("redis_data_structure_flow  len(info['redis']): {}".format(len(info["redis"])))

            if len(info["redis"]) > 0:
                # 计算每台主机部署的节点数
                avg = int(len(cluster_src_instance) // len(info["redis"]))
                # 计算整除后多于的节点数
                remainder = int(len(cluster_src_instance) % len(info["redis"]))
                logger.info("redis_data_structure_flow info['redis']: {}".format(info["redis"]))
            else:
                raise ValueError("info['redis'] len < 0, please check!")
            # ### 部署redis ############################################################
            sub_pipelines_install = []
            cluster_dst_instance = []
            cluster_type = act_kwargs.cluster["cluster_type"]
            resource_spec = info["resource_spec"]["redis"]
            for index, new_master in enumerate([host["ip"] for host in info["redis"]]):
                # 将整除后多于的节点一个一个地分配给每台主机
                instance_numb = avg + 1 if index < remainder else avg
                sub_builder = RedisBatchInstallAtomJob(
                    self.root_id,
                    self.data,
                    act_kwargs,
                    {
                        "ip": new_master,
                        "meta_role": InstanceRole.REDIS_MASTER.value,
                        "start_port": DEFAULT_REDIS_START_PORT,
                        "ports": [],
                        "instance_numb": instance_numb,
                        "spec_id": resource_spec["id"],
                        "spec_config": resource_spec,
                    },
                )
                sub_pipelines_install.append(sub_builder)

                # 将部署信息存入cluster_dst_instance
                for inst_no in range(0, instance_numb):
                    port = DEFAULT_REDIS_START_PORT + inst_no
                    cluster_dst_instance.append("{}{}{}".format(new_master, IP_PORT_DIVIDER, port))
            logger.info("redis_data_structure_flow cluster_dst_instance: {}".format(cluster_dst_instance))
            # 检查节点总数是否相等
            if len(info["master_instances"]) != len(cluster_dst_instance):
                raise ValueError("The total number of nodes in both clusters must be equal.")

            # 使用zip函数将源集群和临时集群的节点一一对应
            node_pairs = list(zip(cluster_src_instance, cluster_dst_instance))
            logger.info(_("redis_data_structure_flow 源集群和临时集群的节点一一对应关系node_pairs: {}".format(node_pairs)))
            # ### 下发actuator包############################################################
            acts_lists = []
            first_act_kwargs = deepcopy(act_kwargs)
            for index, new_master in enumerate([host["ip"] for host in info["redis"]]):
                trans_files = GetFileList(db_type=DBType.Redis)
                first_act_kwargs.file_list = trans_files.redis_actuator_backend()
                first_act_kwargs.exec_ip = new_master
                acts_lists.append(
                    {
                        "act_name": _("Redis-{}-下发actuator包").format(new_master),
                        "act_component_code": TransFileComponent.code,
                        "kwargs": asdict(first_act_kwargs),
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list=acts_lists)
            # ### 下发actuator包完成############################################################

            # ###  初始化机器，有时机器混用环境变量没处理，会导致部分目录不存在，会有影响###############
            acts_lists = []
            first_act_kwargs = deepcopy(act_kwargs)
            for index, new_master in enumerate([host["ip"] for host in info["redis"]]):
                first_act_kwargs.exec_ip = new_master
                first_act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
                acts_lists.append(
                    {
                        "act_name": _("初始化机器"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(first_act_kwargs),
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list=acts_lists)
            # ### 初始化机器完成############################################################

            # ###安装备份环境##########################################################################
            new_master_list = []

            for index, new_master in enumerate([host["ip"] for host in info["redis"]]):
                # 将new_master添加到列表中
                new_master_list.append(new_master)
            redis_pipeline.add_act(
                act_name=_("Redis-安装backup-client工具-{}").format(new_master_list),
                act_component_code=DownloadBackupClientComponent.code,
                kwargs=asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=act_kwargs.cluster["bk_cloud_id"],
                        bk_biz_id=int(act_kwargs.cluster["bk_biz_id"]),
                        download_host_list=new_master_list,
                    ),
                ),
            )
            # ###  安装备份环境结束##########################################################################

            # # ### 获取机器磁盘备份目录信息 ##########################################################

            first_act_kwargs = deepcopy(act_kwargs)
            ip_list = [host["ip"] for host in info["redis"]]
            first_act_kwargs.exec_ip = ip_list

            first_act_kwargs.write_op = WriteContextOpType.APPEND.value
            first_act_kwargs.cluster[
                "shell_command"
            ] = """
                REDIS_DATA_DIR_DATA=`df -k $REDIS_DATA_DIR | grep -iv Filesystem`
                REDIS_BACKUP_DIR_DATA=`df -k $REDIS_BACKUP_DIR | grep -iv Filesystem`
                BACKUP_DIR=`echo $REDIS_BACKUP_DIR`
                mkdir -p $BACKUP_DIR/dbbak/recover_redis/
                chown -R  mysql:mysql $BACKUP_DIR/dbbak/recover_redis/
                echo "<ctx>{\\\"redis_data_dir_data\\\":\\\"${REDIS_DATA_DIR_DATA}\\\", \\
                \\\"backup_dir\\\":\\\"${BACKUP_DIR}\\\",\\\"redis_backup_dir_data\\\":\\\"${REDIS_BACKUP_DIR_DATA}\\\"}</ctx>"
                """
            redis_pipeline.add_act(
                act_name=_("获取磁盘使用情况: {}").format(ip_list),
                act_component_code=ExecuteShellScriptComponent.code,
                kwargs=asdict(first_act_kwargs),
                write_payload_var="disk_used",
            )

            # ### 获取机器磁盘备份目录信息结束############################################################

            # ### 数据构造下发actuator 检查备份文件是否存在，新机器磁盘空间是否够##############################################
            tendis_type = self.get_tendis_type_by_cluster_type(cluster_type)
            # 目录设置为空，根据获取到的机器备份目录来设置
            dest_dir = ""
            # 整理数据构造下发actuator 源节点和临时集群节点之间的对应关系，# 获取备份信息，用于磁盘空间是否足够的前置检查
            acts_list, acts_list_push_json = self.get_prod_temp_instance_pairs(
                act_kwargs, node_pairs, info, tendis_type, dest_dir
            )
            logger.info(_("redis_data_structure_flow acts_list_push_json: {}".format(acts_list_push_json)))

            # ### 检查新机器磁盘空间和内存是否够##############################################
            acts_list_disk_check = self.generate_acts_list_disk_check(
                info["redis"], acts_list, cluster_type, first_act_kwargs
            )
            redis_pipeline.add_parallel_acts(acts_list=acts_list_disk_check)

            # 并发下载 节点维度的备份文件
            sub_pipelines = []
            for act in acts_list:
                data_params = act["kwargs"]["cluster"]
                # source_ports = data_params["source_ports"]
                # for source_port in source_ports:
                # 这里可以一次下载，不用按端口分批下载
                sub_builder = redis_backupfile_download(
                    self.root_id,
                    self.data,
                    info,
                    {
                        "source_ip": data_params["source_ip"],
                        # "source_port": source_port,
                        "new_temp_ip": data_params["new_temp_ip"],
                        "full_file_list": data_params["full_file_list"],
                        "binlog_file_list": data_params["binlog_file_list"],
                        "dest_dir": data_params["dest_dir"],
                        "tendis_type": data_params["tendis_type"],
                    },
                )
                sub_pipelines.append(sub_builder)
                # 并发下载
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

            # 检查备份信息存在，机器磁盘是否够，然后下载到临时机器，这里最后再部署redis 节点，免得做无用步骤
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines_install)

            # # ###cc 转移机器模块 ################################################################
            # 直接挪机器
            cluster_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_rollback_host_transfer.__name__
            cluster_kwargs.cluster["tendiss"] = []
            for instance in cluster_dst_instance:
                ip, port = instance.split(":")
                cluster_kwargs.cluster["tendiss"].append({"receiver": {"ip": ip, "port": int(port)}})
            redis_pipeline.add_act(
                act_name=_("Redis-临时节点加入源集群cc模块"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(cluster_kwargs),
            )
            # # ### cc 转移机器模块完成 ############################################################

            # ### 如果是tendisplus,需要构建tendis cluster关系 ############################################################
            if cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
                logger.info("cluster_type is:{} need tendis cluster relation".format(cluster_type))
                act_kwargs.cluster["all_instance"] = cluster_dst_instance
                act_kwargs.get_redis_payload_func = RedisActPayload.rollback_clustermeet_payload.__name__
                # 选第一台作为下发执行任务的机器
                act_kwargs.exec_ip = info["redis"][0]["ip"]
                redis_pipeline.add_act(
                    act_name=_("建立meet关系"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
            # ### 构建tendisplus集群关系结束 #############################################################################

            # ### 部署proxy实例 #############################################################################
            # 选第一台机器作为部署proxy的机器
            act_kwargs.new_install_proxy_exec_ip = info["redis"][0]["ip"]
            act_kwargs.get_trans_data_ip_var = RedisDataStructureContext.get_proxy_exec_ip_var_name()

            trans_files = GetFileList(db_type=DBType.Redis)
            if cluster_type in [
                ClusterType.TendisTwemproxyRedisInstance.value,
                ClusterType.TwemproxyTendisSSDInstance.value,
            ]:
                # 部署proxy pkg包
                act_kwargs.file_list = trans_files.redis_cluster_apply_proxy(cluster_type)
                proxy_payload = RedisActPayload.add_twemproxy_payload.__name__
            elif cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
                act_kwargs.file_list = trans_files.tendisplus_apply_proxy()
                proxy_payload = RedisActPayload.add_predixy_payload.__name__
            else:
                raise NotImplementedError("Not supported cluster type: %s" % cluster_type)

            act_kwargs.get_trans_data_ip_var = RedisDataStructureContext.get_proxy_exec_ip_var_name()
            act_kwargs.exec_ip = act_kwargs.new_install_proxy_exec_ip
            redis_pipeline.add_act(
                act_name=_("{}proxy下发介质包").format(act_kwargs.exec_ip),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 构造proxy server信息
            if cluster_type in [ClusterType.TendisTwemproxyRedisInstance, ClusterType.TwemproxyTendisSSDInstance]:
                servers = self.cal_twemproxy_serveres("admin", act_kwargs.cluster["redis_slave_set"], node_pairs)
            elif cluster_type == ClusterType.TendisPredixyTendisplusCluster:
                servers = cluster_dst_instance
            else:
                raise NotImplementedError("Not supported cluster type: %s" % cluster_type)

            act_kwargs.cluster["servers"] = servers
            logger.info("proxy servers: {}".format(act_kwargs.cluster["servers"]))
            act_kwargs.get_redis_payload_func = proxy_payload
            act_kwargs.exec_ip = act_kwargs.new_install_proxy_exec_ip
            redis_pipeline.add_act(
                act_name=_("{}安装proxy实例").format(act_kwargs.new_install_proxy_exec_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            # ### 数据构造payload json下发 #########################################################################
            redis_pipeline.add_parallel_acts(acts_list=acts_list_push_json)
            # ### 数据构造下发actuator #############################################################################
            redis_pipeline.add_parallel_acts(acts_list=acts_list)

            # # ###  # ### 如果是tendisplus,需要重新构建 cluster关系,因为tendisplus数据构造需要reset集群关系  ##############
            if cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
                logger.info("cluster_type is:{}  cluster  meet and check finish relation".format(cluster_type))
                act_kwargs.cluster["all_instance"] = cluster_dst_instance
                act_kwargs.get_redis_payload_func = RedisActPayload.clustermeet_check_payload.__name__
                # 选第一台作为下发执行任务的机器
                act_kwargs.exec_ip = info["redis"][0]["ip"]
                redis_pipeline.add_act(
                    act_name=_("meet建立集群关系并检查集群状态"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

            # ### 写入构造记录元数据 ######################################################
            act_kwargs.cluster = {
                # 记录元数据
                "domain_name": act_kwargs.cluster["domain_name"],
                "bk_cloud_id": act_kwargs.cluster["bk_cloud_id"],
                "prod_cluster_type": cluster_type,
                "prod_cluster": act_kwargs.cluster["domain_name"],
                "prod_cluster_id": info["cluster_id"],
                "specification": resource_spec,
                "prod_instance_range": cluster_src_instance,
                "temp_cluster_type": cluster_type,
                "temp_instance_range": cluster_dst_instance,
                "temp_cluster_proxy": "{}:{}".format(
                    act_kwargs.new_install_proxy_exec_ip, act_kwargs.cluster["proxy_port"]
                ),
                "prod_temp_instance_pairs": node_pairs,
                "host_count": len(info["redis"]),
                "recovery_time_point": info["recovery_time_point"],
                "status": DataStructureStatus.COMPLETED,
                "meta_func_name": RedisDBMeta.data_construction_tasks_operate.__name__,
                "cluster_type": cluster_type,
            }
            redis_pipeline.add_act(
                act_name=_("写入构造记录元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )

            sub_pipelines_multi_cluster.append(
                redis_pipeline.build_sub_process(sub_name=_("集群[{}]数据构造").format(act_kwargs.cluster["domain_name"]))
            )

        redis_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines_multi_cluster)
        redis_pipeline_all.run_pipeline()

    @staticmethod
    def generate_acts_list_disk_check(
        redis_hosts: List[Dict], acts_list: List[Dict], cluster_type: str, first_act_kwargs: ActKwargs
    ) -> List:
        acts_list_disk_check = []
        for index, new_master in enumerate([host["ip"] for host in redis_hosts]):
            # 计算待下载的备份文件大小和获取对应机器磁盘大小,这里是单个任务的时候，还有多个任务的时候
            multi_total_size = 0
            for act in acts_list:
                data_params = act["kwargs"]["cluster"]
                logger.info(_("generate_acts_list_disk_check_data_params: {}".format(data_params)))
                full_size = 0
                all_binlog_size = 0
                for full in data_params["full_file_list"]:
                    logger.info(_("generate_acts_list_disk_check full: {}".format(full)))
                    full_size += int(full["size"])
                # ssd和tendisplus才有binlog文件
                if cluster_type in [
                    ClusterType.TendisTwemproxyRedisInstance.value,
                    ClusterType.TwemproxyTendisSSDInstance.value,
                ]:
                    for binlog in data_params["binlog_file_list"]:
                        logger.info(_("generate_acts_list_disk_check binlog: {}".format(binlog)))
                        all_binlog_size += int(binlog["size"])
                total_size = full_size + all_binlog_size
                if data_params["new_temp_ip"] == new_master:
                    multi_total_size += total_size
            first_act_kwargs.cluster["multi_total_size"] = multi_total_size
            first_act_kwargs.exec_ip = new_master
            acts_list_disk_check.append(
                {
                    "act_name": _("redis 数据构造前置磁盘检查").format(first_act_kwargs.exec_ip),
                    "act_component_code": RedisDataStructurePrecheckComponent.code,
                    "kwargs": asdict(first_act_kwargs),
                    "splice_payload_var": "disk_used",
                }
            )
        return acts_list_disk_check

    @staticmethod
    def get_tendis_type_by_cluster_type(cluster_type: str) -> str:
        if cluster_type == ClusterType.TendisTwemproxyRedisInstance.value:
            tendis_type = ClusterType.RedisInstance.value
        elif cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
            tendis_type = ClusterType.TendisplusInstance.value
        elif cluster_type == ClusterType.TwemproxyTendisSSDInstance.value:
            tendis_type = ClusterType.TendisSSDInstance.value
        else:
            raise NotImplementedError("Not supported tendis type: %s" % cluster_type)
        logger.info(_("redis_data_structure_flow cluster_type: {}".format(cluster_type)))
        return tendis_type

    @staticmethod
    def get_slave_instance_by_master(master_instances: list, act_kwargs: ActKwargs) -> list:
        cluster_src_instance = []
        if master_instances:
            for master_instance in master_instances:
                if master_instance in act_kwargs.cluster["master_ins_map"]:
                    slave_instance = act_kwargs.cluster["master_ins_map"][master_instance]
                    cluster_src_instance.append(slave_instance)

        return cluster_src_instance

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群现有信息
        1. slave 对应 master 机器
        2. slave 上的端口列表
        3. 实例对应关系：{slave:port : master:port}
        """

        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        slave_master_map = defaultdict()
        slave_ports = defaultdict(list)
        slave_ins_map = defaultdict()
        master_ins_map = defaultdict()
        master_nums = len(cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value))
        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            slave_ports[slave_obj.machine.ip].append(slave_obj.port)
            slave_ins_map["{}{}{}".format(slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port)] = "{}{}{}".format(
                master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port
            )
            master_ins_map["{}{}{}".format(master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port)] = "{}{}{}".format(
                slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port
            )

            ifmaster = slave_master_map.get(slave_obj.machine.ip)
            if ifmaster and ifmaster != master_obj.machine.ip:
                raise Exception(
                    "unsupport mutil master for cluster {}:{}".format(cluster.immute_domain, slave_obj.machine.ip)
                )

            slave_master_map[slave_obj.machine.ip] = master_obj.machine.ip

        cluster_info = api.cluster.nosqlcomm.get_cluster_detail(cluster_id)[0]
        cluster_name = cluster_info["name"]
        cluster_type = cluster_info["cluster_type"]
        redis_slave_set = ""
        if cluster_type in [ClusterType.TendisTwemproxyRedisInstance, ClusterType.TwemproxyTendisSSDInstance]:
            redis_slave_set = cluster_info["redis_slave_set"]

        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "cluster_name": cluster_name,
            "proxy_port": cluster_info["twemproxy_ports"][0],
            "master_nums": master_nums,
            "slave_ports": dict(slave_ports),
            "slave_ins_map": dict(slave_ins_map),
            "slave_master_map": dict(slave_master_map),
            "master_ins_map": dict(master_ins_map),
            "db_version": cluster.major_version,
            "domain_name": cluster_info["clusterentry_set"]["dns"][0]["domain"],
            "redis_slave_set": redis_slave_set,
        }

    def __init_builder(self, operate_name: str, info: dict):
        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], info["cluster_id"])
        logger.info(_("__init_builder_cluster_info: {}".format(cluster_info)))
        flow_data = self.data
        flow_data.update(cluster_info)

        redis_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = RedisDataStructureContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **cluster_info,
            "operate": operate_name,
        }
        act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
        logger.info("+===+++++===current tick_data info+++++===++++ :: {}".format(act_kwargs))

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        return redis_pipeline, act_kwargs

    def __get_cluster_config(self, domain_name: str, db_version: str, conf_type: str, namespace: str) -> Any:
        """
        获取已部署的实例配置
        """
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(self.data["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": domain_name,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": db_version,
                "conf_type": conf_type,
                "namespace": namespace,
                "format": FormatType.MAP,
            }
        )
        return data["content"]

    def cal_twemproxy_serveres(self, name, redis_slave_set, node_pairs) -> list:
        """
        计算twemproxy的servers 列表
        - redisip:redisport:1 app beginSeg-endSeg 1
        "servers": ["1.1.1.1:30000  xxx 0-219999 1","1.1.1.1:30001  xxx 220000-419999 1"]
        """
        # actuator 会校验seg_range和是否为420000
        miss_range_instance = "127.0.0.1:6379"
        servers = []
        node_dict = dict(node_pairs)
        for slave in redis_slave_set:
            instance, seg_range = slave.split(" ")
            servers.append("{} {} {} 1".format(node_dict.get(instance, miss_range_instance), name, seg_range))
        return servers

    def get_prod_temp_instance_pairs(
        self,
        sub_kwargs: ActKwargs,
        node_pairs: list,
        info: dict,
        tendis_type: str,
        dest_dir: str,
    ) -> (list, list):
        # ### 整理 数据构造源节点和临时集群节点之间的对应关系 ######################################################
        """
        1、有一对多：1台源主机对应多台临时主机->加快数据构造进度
        2、有多对一：多台源主机对应一台临时主机->节省成本
        下发actuator 格式：
        {
            "source_ip":"127.0.0.1",
            "source_ports":[30000,30001,30002],
            "new_temp_ip":"127.0.0.2",
            "new_temp_ports":[13000,13001,13002],
            "recovery_time_point":"2023-05-09 22:44:53"
        }
        即，源主机只能有一个(备份系统按主机查询的，而且咱们的部署方式也是主机维度的)，临时的IP，即下发actuator的IP也只能有一个（这个决定了后面节点下发对应关系）
        todo 源主机可以是多台，传入形式改为ip:port ?
        """

        """
        新增 2、找对应关系时就决定了，那些ip需要下发那些文件：
            2.1 还是按照ip+port 的方式查询
            {
                "source_ip":"127.0.0.1",
                "source_ports":[
                    30000,
                    30001,
                    30002
                ],
                "new_temp_ip":"127.0.0.2",
                "new_temp_ports":[
                    13000,
                    13001,
                    13002
                ],
                "recovery_time_point":"2023-12-15 04:15:55.860498+00:00" # 时间戳格式,
                "tendis_type":"RedisInstance",
                "dest_dir":"$REDIS_BACKUP_DIR/dbbak/recover_redis",
                "full_file_list":[
                    {
                        "file_tag":"REDIS_FULL",
                        "status":"success",
                        "uptime":"2023-08-24 01:46:53",
                        "file_last_mtime":"2023-08-24 01:43:30",
                        "size":178635,
                        "source_ip":"xxxx",
                        "task_id":"1692870412566863699-0514017472-22072-0",
                        "file_name":"3-redis-slave-xxx-xxx-20230824-174325.aof.zst"
                    }
                ],
                "binlog_file_list":[
                    {
                        "file_tag":"REDIS_BINLOG",
                        "status":"to_backup_system_success",
                        "uptime":"2023-10-07 05:58:47",
                        "file_last_mtime":"2023-10-07 05:37:51",
                        "size":5734,
                        "source_ip":"xxxx",
                        "task_id":"1696629732091541786-0160215607-30893-0",
                        "file_name":"binlog-xxxx-30000-0004173-20231007053751.log.zst"
                    }
                ]
            }
        """

        # 并发执行redis数据构造
        act_kwargs = deepcopy(sub_kwargs)
        acts_list = []
        acts_list_push_json = []

        rollback_time = info["recovery_time_point"]
        logger.info(_("get_prod_temp_instance_pairs rollback_time: {}".format(rollback_time)))
        kvstorecount = None
        if tendis_type == ClusterType.TendisplusInstance.value:
            kvstorecount = act_kwargs.cluster["kvstorecount"]
        for new_temp_ip in [host["ip"] for host in info["redis"]]:
            source_ports = []
            new_temp_ports = []
            full_backupinfo = []
            binlog_backupinfo = []
            # 遍历所有
            new_temp_node_pairs = []
            source_ip_map = set()
            for pair in node_pairs:
                # 找到新机器相同的对应关系,source_ip可能有多个
                if new_temp_ip in str(pair):
                    new_temp_node_pairs.append(pair)
                    source_ip_map.add(pair[0].split(IP_PORT_DIVIDER)[0])
                    source_ports.append(int(pair[0].split(IP_PORT_DIVIDER)[1]))
                    new_temp_ports.append(int(pair[1].split(IP_PORT_DIVIDER)[1]))
            logger.info(_("new_temp_node_pairs: {}".format(new_temp_node_pairs)))
            # 将多个source_ip的情况继续拆分,每个source_ip是一个actuator
            if len(source_ip_map) > 1:
                logger.info(_("len(source_ip_map) > 1, source_ip_map: {}".format(source_ip_map)))
                for source_temp_ip in source_ip_map:
                    source_ports = []
                    new_temp_ports = []
                    source_ip = ""
                    for temp_pair in new_temp_node_pairs:
                        # 找到新机器相同的对应关系,source_ip只有一个
                        if source_temp_ip in str(temp_pair):
                            source_ports.append(int(temp_pair[0].split(IP_PORT_DIVIDER)[1]))
                            new_temp_ports.append(int(temp_pair[1].split(IP_PORT_DIVIDER)[1]))
                        source_ip = source_temp_ip

                    for source_port in source_ports:
                        logger.info(_("source_ip_map_source_ports: {}".format(source_ports)))
                        instance_full_backup, instance_binlog_backup = self.get_backupfile(
                            info["cluster_id"], rollback_time, source_ip, source_port, tendis_type, kvstorecount
                        )
                        full_backupinfo.append(instance_full_backup)
                        binlog_backupinfo.extend(instance_binlog_backup)
                    acts_list_new_ip, acts_list_push_json_new_ip = self.get_acts_list(
                        source_ip,
                        source_ports,
                        new_temp_ip,
                        new_temp_ports,
                        info["recovery_time_point"],
                        tendis_type,
                        dest_dir,
                        full_backupinfo,
                        binlog_backupinfo,
                        act_kwargs,
                    )
                    acts_list.append(acts_list_new_ip)
                    acts_list_push_json.append(acts_list_push_json_new_ip)
            elif len(source_ip_map) == 1:
                logger.info(_("get_prod_temp_instance_pairs len(source_ip_map) = 1"))
                source_ip = next(iter(source_ip_map))
                for source_port in source_ports:
                    full_backup, binlog_backup = self.get_backupfile(
                        info["cluster_id"], rollback_time, source_ip, source_port, tendis_type, kvstorecount
                    )
                    full_backupinfo.append(full_backup)
                    binlog_backupinfo.extend(binlog_backup)

                acts_list_new_ip, acts_list_push_json_new_ip = self.get_acts_list(
                    source_ip,
                    source_ports,
                    new_temp_ip,
                    new_temp_ports,
                    info["recovery_time_point"],
                    tendis_type,
                    dest_dir,
                    full_backupinfo,
                    binlog_backupinfo,
                    act_kwargs,
                )
                acts_list.append(acts_list_new_ip)
                acts_list_push_json.append(acts_list_push_json_new_ip)
        logger.info(_("redis_data_structure_flow_full_backupinfo: {}".format(full_backupinfo)))
        logger.info(_("redis_data_structure_flow_binlog_backupinfo: {}".format(binlog_backupinfo)))
        return acts_list, acts_list_push_json

    @staticmethod
    def get_backupfile(cluster_id, rollback_time, source_ip, source_port, tendis_type, kvstorecount) -> (dict, dict):
        rollback_handler = DataStructureHandler(cluster_id)
        instance_binlog_backup = []
        instance_full_backup = rollback_handler.query_latest_backup_log(
            str2datetime(rollback_time), source_ip, source_port
        )
        if instance_full_backup is None:
            raise TendisGetBinlogFailedException(message=_("获取实例 {}:{} 的binlog备份信息失败".format(source_ip, source_port)))
        # 全备份的开始时间
        # TODO: Timestamp改造，这一块后续采集项会改成时区时间，待验证
        backup_time = instance_full_backup["file_last_mtime"]
        # ssd 和tendisplus才有binlog
        if tendis_type in [ClusterType.TendisplusInstance.value, ClusterType.TendisSSDInstance.value]:
            # 查询binlog
            instance_binlog_backup = rollback_handler.query_binlog_from_bklog(
                start_time=str2datetime(backup_time),
                end_time=str2datetime(rollback_time),
                minute_range=120,
                host_ip=source_ip,
                port=source_port,
                kvstorecount=kvstorecount,
                tendis_type=tendis_type,
            )

            if instance_binlog_backup is None:
                raise TendisGetBinlogFailedException(
                    message=_("获取实例 {}:{} 的binlog备份信息失败".format(source_ip, source_port))
                )

        return instance_full_backup, instance_binlog_backup

    @staticmethod
    def get_acts_list(
        source_ip,
        source_ports,
        new_temp_ip,
        new_temp_ports,
        recovery_time_point,
        tendis_type,
        dest_dir,
        full_backupinfo,
        binlog_backupinfo,
        act_kwargs,
    ) -> (dict, dict):
        act_kwargs.cluster["source_ip"] = source_ip
        act_kwargs.cluster["source_ports"] = source_ports
        act_kwargs.cluster["new_temp_ip"] = new_temp_ip
        act_kwargs.cluster["new_temp_ports"] = new_temp_ports
        act_kwargs.cluster["recovery_time_point"] = recovery_time_point
        act_kwargs.cluster["tendis_type"] = tendis_type
        act_kwargs.cluster["dest_dir"] = dest_dir
        act_kwargs.cluster["full_file_list"] = full_backupinfo
        act_kwargs.cluster["binlog_file_list"] = binlog_backupinfo

        act_kwargs.exec_ip = new_temp_ip
        act_kwargs.get_redis_payload_func = RedisActPayload.redis_data_structure.__name__
        act_kwargs.act_name = _("源{}构造到临时机{}").format(source_ip, act_kwargs.exec_ip)
        node_acts_list_push_json = {
            "act_name": _("源{}payload json下发到临时机{}").format(source_ip, act_kwargs.exec_ip),
            "act_component_code": PushDataStructureJsonScriptComponent.code,
            "kwargs": asdict(act_kwargs),
        }
        node_acts_list = {
            "act_name": act_kwargs.act_name,
            "act_component_code": ExecuteDataStructureActuatorScriptComponent.code,
            "kwargs": asdict(act_kwargs),
        }

        return node_acts_list, node_acts_list_push_json
