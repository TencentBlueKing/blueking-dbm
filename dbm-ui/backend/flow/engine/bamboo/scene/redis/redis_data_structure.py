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
from typing import Any, Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_DB_MODULE_ID, DEFAULT_REDIS_START_PORT, DEFAULT_TWEMPROXY_SEG_TOTOL_NUM
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisBatchInstallAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, RedisDataStructureContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

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
             "master_instance":[
                "127.0.0.1:30000", "127.0.0.1:30002"
            ],
            "recovery_time_point": "2022-12-12 11:11:11",
            "redis_data_structure_hosts": [
                {"ip": "3.3.3.1", "bk_cloud_id": 0, "bk_host_id": 2},
                {"ip": "3.3.3.2", "bk_cloud_id": 0, "bk_host_id": 2},
            ]
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
            # 源节点列表
            cluster_src_instance = []
            # sass 层传入节点信息（集群维度传入所有节点）
            if len(info["master_instance"]) != 0:
                # 根据传入的master_instance 获取其slave_instance
                for slave_instance, master_instance in act_kwargs.cluster["slave_ins_map"].items():
                    for backup_master_instance in info["master_instance"]:
                        if backup_master_instance == master_instance:
                            cluster_src_instance.append(slave_instance)
            try:
                if len(info["redis_data_structure_hosts"]) != 0 and len(cluster_src_instance) != 0:
                    # 计算每台主机部署的节点数
                    avg = int(len(cluster_src_instance) // len(info["redis_data_structure_hosts"]))
                    # 计算整除后多于的节点数
                    remainder = int(len(cluster_src_instance) % len(info["redis_data_structure_hosts"]))
            except ZeroDivisionError:
                logger.info("divisor cannot be zero！")
            logger.info("redis_data_structure_flow cluster_src_instance: {}".format(cluster_src_instance))

            # ### 部署redis ############################################################
            sub_pipelines = []
            cluster_dst_instance = []
            for index, new_master in enumerate([host["ip"] for host in info["redis_data_structure_hosts"]]):
                # 将整除后多于的节点一个一个地分配给每台主机
                if index < remainder:
                    instance_numb = avg + 1
                else:
                    instance_numb = avg
                params = {
                    "ip": new_master,
                    "meta_role": InstanceRole.REDIS_MASTER.value,
                    "start_port": DEFAULT_REDIS_START_PORT,
                    "ports": [],
                    "instance_numb": instance_numb,
                    # 资源池新增 先固定为0
                    "spec_id": 0,
                    "spec_config": "xx",
                }
                sub_builder = RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
                sub_pipelines.append(sub_builder)
                # 将部署信息存入cluster_dst_instance
                for inst_no in range(0, instance_numb):
                    port = DEFAULT_REDIS_START_PORT + inst_no
                    cluster_dst_instance.append("{}:{}".format(new_master, port))
                    # cluster_dst_instance.append(new_master + ":" + str(DEFAULT_REDIS_START_PORT + i))
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

            # ### 如果是tendisplus,需要构建tendis cluster关系 ############################################################
            if act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
                logger.info(
                    "cluster_type is:{} need tendis cluster relation".format(act_kwargs.cluster["cluster_type"])
                )
                act_kwargs.cluster["all_instance"] = cluster_dst_instance
                act_kwargs.get_redis_payload_func = RedisActPayload.rollback_clustermeet_payload.__name__
                # 选第一台作为下发执行任务的机器
                act_kwargs.exec_ip = info["redis_data_structure_hosts"][0]["ip"]
                redis_pipeline.add_act(
                    act_name=_("建立meet关系"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
            # ### 构建tendisplus集群关系结束 #############################################################################

            # ### 部署proxy实例 #############################################################################
            # 选第一台机器作为部署proxy的机器
            act_kwargs.new_install_proxy_exec_ip = info["redis_data_structure_hosts"][0]["ip"]
            act_kwargs.get_trans_data_ip_var = RedisDataStructureContext.get_proxy_exec_ip_var_name()
            proxy_payload = ""
            trans_files = GetFileList(db_type=DBType.Redis)
            if act_kwargs.cluster["cluster_type"] in [
                ClusterType.TendisTwemproxyRedisInstance.value,
                ClusterType.TwemproxyTendisSSDInstance.value,
            ]:
                # 部署proxy pkg包
                act_kwargs.file_list = trans_files.redis_cluster_apply_proxy(act_kwargs.cluster["cluster_type"])
                proxy_payload = RedisActPayload.add_twemproxy_payload.__name__
            elif act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
                act_kwargs.file_list = trans_files.tendisplus_apply_proxy()
                proxy_payload = RedisActPayload.add_predixy_payload.__name__
            else:
                pass
            act_kwargs.get_trans_data_ip_var = RedisDataStructureContext.get_proxy_exec_ip_var_name()
            act_kwargs.exec_ip = act_kwargs.new_install_proxy_exec_ip
            redis_pipeline.add_act(
                act_name=_("{}proxy下发介质包").format(act_kwargs.exec_ip),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )
            act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
            redis_pipeline.add_act(
                act_name=_("初始化机器"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            redis_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            # # 检查节点总数是否相等
            if len(info["master_instance"]) != len(cluster_dst_instance):
                raise ValueError("The total number of nodes in both clusters must be equal.")

            # 构造proxy server信息
            if (
                act_kwargs.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance
                or act_kwargs.cluster["cluster_type"] == ClusterType.TwemproxyTendisSSDInstance
            ):
                servers = self.cal_twemproxy_serveres("admin", len(info["master_instance"]), cluster_dst_instance)
            elif act_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster:
                servers = cluster_dst_instance
            act_kwargs.cluster["servers"] = servers
            logger.info("proxy servers: {}".format(act_kwargs.cluster["servers"]))
            act_kwargs.get_redis_payload_func = proxy_payload
            act_kwargs.exec_ip = act_kwargs.new_install_proxy_exec_ip
            redis_pipeline.add_act(
                act_name=_("{}安装proxy实例").format(act_kwargs.new_install_proxy_exec_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # ### 数据构造下发actuator #############################################################################
            # 使用zip函数将源集群和临时集群的节点一一对应
            node_pairs = list(zip(cluster_src_instance, cluster_dst_instance))
            # 整理数据构造下发actuator 源节点和临时集群节点之间的对应关系，
            acts_list = self.get_prod_temp_instance_pairs(act_kwargs, node_pairs, info)
            redis_pipeline.add_parallel_acts(acts_list=acts_list)

            # ### 写入构造记录元数据 ######################################################
            act_kwargs.cluster = {
                # 记录元数据
                "domain_name": act_kwargs.cluster["domain_name"],
                "bk_cloud_id": act_kwargs.cluster["bk_cloud_id"],
                "prod_cluster_type": act_kwargs.cluster["cluster_type"],
                "prod_cluster": act_kwargs.cluster["domain_name"],
                "prod_instance_range": cluster_src_instance,
                "temp_cluster_type": act_kwargs.cluster["cluster_type"],
                "temp_instance_range": cluster_dst_instance,
                "temp_cluster_proxy": "{}:{}".format(
                    act_kwargs.new_install_proxy_exec_ip, act_kwargs.cluster["proxy_port"]
                ),
                "prod_temp_instance_pairs": node_pairs,
                "host_count": len(info["redis_data_structure_hosts"]),
                "recovery_time_point": info["recovery_time_point"],
                "status": 2,
                "meta_func_name": RedisDBMeta.data_construction_tasks_operate.__name__,
                "cluster_type": act_kwargs.cluster["cluster_type"],
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
        master_nums = len(cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value))
        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            slave_ports[slave_obj.machine.ip].append(slave_obj.port)
            slave_ins_map["{}:{}".format(slave_obj.machine.ip, slave_obj.port)] = "{}:{}".format(
                master_obj.machine.ip, master_obj.port
            )

            ifmaster = slave_master_map.get(slave_obj.machine.ip)
            if ifmaster and ifmaster != master_obj.machine.ip:
                raise Exception(
                    "unsupport mutil master for cluster {}:{}".format(cluster.immute_domain, slave_obj.machine.ip)
                )
            else:
                slave_master_map[slave_obj.machine.ip] = master_obj.machine.ip

        cluster_info = api.cluster.nosqlcomm.get_cluster_detail(cluster_id)[0]
        cluster_name = cluster_info["name"]

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
            "db_version": cluster.major_version,
            "domain_name": cluster_info["clusterentry_set"]["dns"][0]["domain"],
        }

    def __init_builder(self, operate_name: str, info: dict):
        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], info["cluster_id"])
        flow_data = self.data
        for k, v in cluster_info.items():
            flow_data[k] = v
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

    def cal_twemproxy_serveres(self, name, shard_num, redis_instance_list) -> list:
        """
        计算twemproxy的servers 列表
        - redisip:redisport:1 app beginSeg-endSeg 1
        "servers": ["1.1.1.1:30000  xxx 0-219999 1","1.1.1.1:30001  xxx 220000-419999 1"]
        """
        shard_num = shard_num
        name = name
        seg_num = DEFAULT_TWEMPROXY_SEG_TOTOL_NUM // shard_num
        seg_no = 0
        #  计算分片
        servers = []
        for index, instance in enumerate(redis_instance_list):
            begin_seg = seg_no * seg_num
            end_seg = seg_num * (seg_no + 1) - 1
            # 最后一个节点 seg_num 不能整除的情况
            if index == len(redis_instance_list) - 1 and end_seg != DEFAULT_TWEMPROXY_SEG_TOTOL_NUM:
                end_seg = DEFAULT_TWEMPROXY_SEG_TOTOL_NUM - 1
            seg_no = seg_no + 1
            servers.append(" {} {} {}-{} {}".format(instance, name, begin_seg, end_seg, 1))
        return servers

    def get_prod_temp_instance_pairs(self, sub_kwargs: ActKwargs, node_pairs: list, info: dict) -> list:
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
        # 并发执行redis数据构造
        act_kwargs = deepcopy(sub_kwargs)
        acts_list = []
        for new_temp_ip in [host["ip"] for host in info["redis_data_structure_hosts"]]:

            source_ports = []
            new_temp_ports = []
            source_ip = ""
            # 遍历所有
            new_temp_node_pairs = []
            source_ip_map = set()
            for pair in node_pairs:
                # 找到新机器相同的对应关系,source_ip可能有多个
                if new_temp_ip in str(pair):
                    new_temp_node_pairs.append(pair)
                    source_ip_map.add(pair[0].split(":")[0])
                    source_ports.append(int(pair[0].split(":")[1]))
                    new_temp_ports.append(int(pair[1].split(":")[1]))
            # 将多个source_ip的情况继续拆分,每个source_ip是一个actuator
            if len(source_ip_map) > 1:
                for source_temp_ip in source_ip_map:
                    source_ports = []
                    new_temp_ports = []
                    source_ip = ""
                    for temp_pair in new_temp_node_pairs:
                        # 找到新机器相同的对应关系,source_ip只有一个
                        if source_temp_ip in str(temp_pair):
                            source_ports.append(int(temp_pair[0].split(":")[1]))
                            new_temp_ports.append(int(temp_pair[1].split(":")[1]))
                        source_ip = source_temp_ip
                    data_params = {
                        "source_ip": source_ip,
                        "source_ports": source_ports,
                        "new_temp_ip": new_temp_ip,
                        "new_temp_ports": new_temp_ports,
                        "recovery_time_point": info["recovery_time_point"],
                    }
                    act_kwargs.cluster = {}
                    act_kwargs.cluster["data_params"] = data_params
                    logger.info("Data structure delivery data_params：{}".format(act_kwargs.cluster["data_params"]))
                    act_kwargs.exec_ip = new_temp_ip
                    act_kwargs.get_redis_payload_func = RedisActPayload.redis_data_structure.__name__
                    acts_list.append(
                        {
                            "act_name": _("{}数据构造").format(act_kwargs.exec_ip),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(act_kwargs),
                        }
                    )
            elif len(source_ip_map) == 1:
                source_ip = next(iter(source_ip_map))
                data_params = {
                    "source_ip": source_ip,
                    "source_ports": source_ports,
                    "new_temp_ip": new_temp_ip,
                    "new_temp_ports": new_temp_ports,
                    "recovery_time_point": info["recovery_time_point"],
                }
                act_kwargs.cluster = {}
                act_kwargs.cluster["data_params"] = data_params
                logger.info("Data structure delivery data_params：{}".format(act_kwargs.cluster["data_params"]))
                act_kwargs.exec_ip = new_temp_ip
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_data_structure.__name__
                acts_list.append(
                    {
                        "act_name": _("{}数据构造").format(act_kwargs.exec_ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
        return acts_list
