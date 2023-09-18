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
from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import (
    DEFAULT_LAST_IO_SECOND_AGO,
    DEFAULT_MASTER_DIFF_TIME,
    DEFAULT_REDIS_START_PORT,
    SyncType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    RedisBatchInstallAtomJob,
    RedisBatchShutdownAtomJob,
    RedisClusterSwitchAtomJob,
    RedisDbmonAtomJob,
    RedisMakeSyncAtomJob,
)
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisClusterMasterSceneFlow(object):
    """
    ## Redis cluster Master 裁撤/迁移替换, 成对替换
    {
      "uid": "2022051612120001",
      "cluster_id":111, # 必须有
      "domain_name":"xxx.abc.dba.db",
      "bk_biz_id":"",
      "bk_cloud_id":11,
      "region":"xxxyw", # 可选
      "device_class":"S5.Large8" # 可选
      "ip_source": "manual_input", # 手动输入/自动匹配资源池
      "replace_relation":{"1.1.a.1":[6.6.b.6,7.c.7.7],"2.d.2.2":[8.e.8.8,9.9.f.9] # 可选
      "ticket_type": "REDIS_CLUSTER_MASTER_CUTOFF"
      "created_by":"u r great!",
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群现有信息
        1. master 对应 slave 机器
        2. master 上的端口列表
        3. 实例对应关系：{master:port:slave:port}
        """
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        master_ports = defaultdict(list)
        slave_ports = defaultdict(list)
        ins_pair_map = defaultdict()
        master_slave_map = defaultdict()
        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            master_ports[master_obj.machine.ip].append(master_obj.port)
            slave_ports[slave_obj.machine.ip].append(slave_obj.port)
            ins_pair_map["{}{}{}".format(master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port)] = "{}{}{}".format(
                slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port
            )

            ifslave = master_slave_map.get(master_obj.machine.ip)
            if ifslave and ifslave != slave_obj.machine.ip:
                raise Exception(
                    "unsupport mutil slave with cluster {} 4:{}".format(cluster.immute_domain, master_obj.machine.ip)
                )
            else:
                master_slave_map[master_obj.machine.ip] = slave_obj.machine.ip

        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "cluster_id": cluster.id,
            "slave_ports": dict(slave_ports),
            "master_ports": dict(master_ports),
            "ins_pair_map": dict(ins_pair_map),
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "master_slave_map": dict(master_slave_map),
            "db_version": cluster.major_version,
        }

    def __init_builder(self, operate_name: str):
        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], self.data["cluster_id"])
        sync_type = SyncType.SYNC_MMS  # ssd sync from master
        if cluster_info["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            sync_type = SyncType.SYNC_SMS

        flow_data = self.data
        for k, v in cluster_info.items():
            flow_data[k] = v
        redis_pipeline = Builder(root_id=self.root_id, data=flow_data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **cluster_info,
            "operate": operate_name,
            "sync_type": sync_type,
        }
        act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
        logger.info("+===+++++===+++++===++++current cluster info :: {}".format(cluster_info))
        logger.info("+===+++++===+++++===++++current tick_data info :: {}".format(act_kwargs))

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        return redis_pipeline, act_kwargs

    def work_4_replace(self):
        """### 适用于 集群中Master 机房裁撤/迁移替换场景 (成对替换)

        步骤：   获取变更锁--> 新实例部署-->
                建Sync关系--> 检测同步状态
                Kill Dead链接--> 下架旧实例
        """
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS_MASTER-裁撤替换"))

        # ### 部署实例 #############################################################################
        sub_pipelines = []
        for old_master, new_hosts in self.data["replace_relation"].items():
            for one_host in new_hosts:
                params = {
                    "ip": one_host,
                    "meta_role": InstanceRole.REDIS_MASTER.value,
                    "start_port": DEFAULT_REDIS_START_PORT,
                    "instance_numb": len(act_kwargs.cluster["master_ports"][old_master]),
                }
                sub_builder = RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
                sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # ### 部署实例 ########################################################################## 完毕 ###

        sync_relations, new_slave_ports = [], []  # 按照机器对组合
        # #### 建同步关系 #############################################################################
        sub_pipelines = []
        for old_master, new_hosts in self.data["replace_relation"].items():
            sync_params = {
                "sync_type": act_kwargs.cluster["sync_type"],
                "origin_1": old_master,
                "origin_2": act_kwargs.cluster["master_slave_map"][old_master],
                "sync_dst1": new_hosts[0],
                "sync_dst2": new_hosts[1],
                "ins_link": [],
            }
            new_ins_port = DEFAULT_REDIS_START_PORT
            for old_master_port in act_kwargs.cluster["master_ports"][old_master].sort():
                old_master_ins = "{}{}{}".format(old_master, IP_PORT_DIVIDER, old_master_port)
                old_slave_ins = act_kwargs.cluster["ins_pair_map"][old_master_ins]
                new_slave_ports.append(new_ins_port)
                sync_params["ins_link"].append(
                    {
                        "origin_1": old_master_port,
                        "origin_2": old_slave_ins.split(IP_PORT_DIVIDER)[1],
                        "sync_dst1": new_ins_port,
                        "sync_dst2": new_ins_port,
                    }
                )
                new_ins_port = new_ins_port + 1
                sync_relations.append(sync_params)
            sub_builder = RedisMakeSyncAtomJob(self.root_id, self.data, act_kwargs, sync_params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # ### 建同步关系 ########################################################################## 完毕 ###

        # 执行切换 #############################################################################
        act_kwargs.cluster["switch_condition"] = {
            "is_check_sync": True,  # 不强制切换
            "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
            "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
            "can_write_before_switch": True,
            "sync_type": act_kwargs.cluster["sync_type"],
        }
        sub_pipeline = RedisClusterSwitchAtomJob(self.root_id, self.data, act_kwargs, sync_relations)
        redis_pipeline.add_sub_pipeline(sub_flow=sub_pipeline)
        # #### 执行切换 #############################################################################

        # 刷新监控 #############################################################################
        sub_pipelines = []
        for old_master, new_hosts in self.data["replace_relation"].items():
            params = {
                "ip": new_hosts[1],
                "ports": new_slave_ports,
                "meta_role": InstanceRole.REDIS_SLAVE.value,
                "cluster_name": act_kwargs.cluster["cluster_name"],
                "cluster_type": act_kwargs.cluster["cluster_type"],
                "immute_domain": act_kwargs.cluster["immute_domain"],
            }
            sub_builder = RedisDbmonAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # 刷新监控 ########################################################################## 完毕 ###

        # #### 下架旧实例 #############################################################################
        sub_pipelines = []
        for old_master in self.data["replace_relation"].keys():
            params = {
                "ip": old_master,
                "ports": act_kwargs.cluster["master_ports"][old_master],
            }
            sub_builder = RedisBatchShutdownAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)

            old_slave = act_kwargs.cluster["master_slave_map"][old_master]
            params = {
                "ip": old_slave,
                "ports": act_kwargs.cluster["slave_ports"][old_slave],
            }
            sub_builder = RedisBatchShutdownAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # #### 下架旧实例 ########################################################################## 完毕 ###

        redis_pipeline.run_pipeline()

    def work_4_auotfix(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS_MASTER-故障自愈"))
        # # 探测故障实例状态 ## ## 修改元数据状态 ##
        # # 根据需要申请替换 ##
        # 这里可以直接复用 slave 裁撤场景
        pass
