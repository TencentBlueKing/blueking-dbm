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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_REDIS_START_PORT, SyncType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    RedisBatchInstallAtomJob,
    RedisBatchShutdownAtomJob,
    RedisLocalRepairAtomJob,
    RedisMakeSyncAtomJob,
)
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisClusterSlaveSceneFlow(object):
    """
    ## Redis cluster Slave 裁撤/迁移替换
    {
      "uid": "2022051612120001",
      "cluster_id":111, # 必须有
      "domain_name":"xxx.abc.dba.db",
      "bk_biz_id":"",
      "bk_cloud_id":11,
      "region":"xxxyw", # 可选
      "device_class":"S5.Large8" # 可选
      "ip_source": "manual_input", # 手动输入/自动匹配资源池
      "replace_relation":{"1.1.x.1":"6.6.y.6","2.2.z.2":"7.7.a.7"} # 可选
      "ticket_type": "REDIS_CLUSTER_SLAVE_CUTOFF"
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
        self.__precheck_()

    def __precheck_(self) -> dict:
        cluster = Cluster.objects.get(id=self.data["cluster_id"], bk_biz_id=self.data["bk_biz_id"])
        if not cluster:
            raise Exception(
                "cluster does not exist bk_biz_id:{}, cluster_id{}".format(
                    self.data["bk_biz_id"], self.data["cluster_id"]
                )
            )
        for old_slave in self.data["replace_relation"].keys():
            if not cluster.storageinstance_set.filter(machine__ip=old_slave).exists():
                raise Exception("bad slave for cluster {} slave_not_exists:{}".format(cluster, old_slave))

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
        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            slave_ports[slave_obj.machine.ip].append(slave_obj.port)
            slave_ins_map["{}{}{}".format(slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port)] = "{}{}{}".format(
                master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port
            )

            ifmaster = slave_master_map.get(slave_obj.machine.ip)
            if ifmaster and ifmaster != master_obj.machine.ip:
                raise Exception(
                    "unsupport mutil master for cluster {}:{}".format(cluster.immute_domain, slave_obj.machine.ip)
                )
            else:
                slave_master_map[slave_obj.machine.ip] = master_obj.machine.ip

        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "slave_ports": dict(slave_ports),
            "slave_ins_map": dict(slave_ins_map),
            "slave_master_map": dict(slave_master_map),
            "db_version": cluster.major_version,
        }

    def __init_builder(self, operate_name: str):
        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], self.data["cluster_id"])
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
        }
        act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
        logger.info("+===+++++===current tick_data info+++++===++++ :: {}".format(act_kwargs))

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        return redis_pipeline, act_kwargs

    def work_4_replace(self):
        """适用于 集群中Slave 机房裁撤/迁移替换场景

        步骤：   获取变更锁--> 新实例部署-->
                重建热备--> 检测同步状态-->
                Kill Dead链接--> 下架旧实例
        """
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS_SLAVE-裁撤替换"))

        # ### 部署实例 #############################################################################
        sub_pipelines = []
        for old_slave, new_slave in self.data["replace_relation"].items():
            params = {
                "ip": new_slave,
                "meta_role": InstanceRole.REDIS_SLAVE.value,
                "start_port": DEFAULT_REDIS_START_PORT,
                "ports": act_kwargs.cluster["slave_ports"][old_slave],
                "instance_numb": len(act_kwargs.cluster["slave_ports"][old_slave]),
            }
            sub_builder = RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # ### 部署实例 ########################################################################## 完毕 ###

        # #### 建同步关系 #############################################################################
        sub_pipelines = []
        for old_slave, new_slave in self.data["replace_relation"].items():
            install_params = {
                "sync_type": SyncType.SYNC_MS,
                "origin_1": act_kwargs.cluster["slave_master_map"][old_slave],
                "origin_2": old_slave,
                "sync_dst1": new_slave,
                "ins_link": [],
            }
            for slave_port in act_kwargs.cluster["slave_ports"][old_slave]:
                old_ins = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, slave_port)
                master_port = act_kwargs.cluster["slave_ins_map"].get(old_ins).split(IP_PORT_DIVIDER)[1]
                install_params["ins_link"].append({"origin_1": master_port, "sync_dst1": slave_port})
            sub_builder = RedisMakeSyncAtomJob(self.root_id, self.data, act_kwargs, install_params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # #### 建同步关系 ########################################################################## 完毕 ###

        # 新节点加入集群 #############################################################################
        act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_redo_slaves.__name__
        act_kwargs.cluster["old_slaves"] = []
        act_kwargs.cluster["created_by"] = self.data["created_by"]
        act_kwargs.cluster["tendiss"] = []
        for old_slave, new_slave in self.data["replace_relation"].items():
            act_kwargs.cluster["old_slaves"].append(
                {"ip": old_slave, "ports": act_kwargs.cluster["slave_ports"][old_slave]}
            )
            for slave_port in act_kwargs.cluster["slave_ports"][old_slave]:
                old_ins = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, slave_port)
                master = act_kwargs.cluster["slave_ins_map"].get(old_ins)
                act_kwargs.cluster["tendiss"].append(
                    {
                        "ejector": {
                            "ip": master.split(IP_PORT_DIVIDER)[0],
                            "port": int(master.split(IP_PORT_DIVIDER)[1]),
                        },
                        "receiver": {"ip": new_slave, "port": int(slave_port)},
                    }
                )
        redis_pipeline.add_act(
            act_name=_("Redis-新节点加入集群"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )
        # #### 新节点加入集群 ########################################################################## 完毕 ###

        # #### 下架旧实例 #############################################################################
        sub_pipelines = []
        for old_slave in self.data["replace_relation"].keys():
            params = {
                "ignore_ips": act_kwargs.cluster["slave_master_map"][old_slave],
                "ip": old_slave,
                "ports": act_kwargs.cluster["slave_ports"][old_slave],
            }
            sub_builder = RedisBatchShutdownAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # #### 下架旧实例 ########################################################################## 完毕 ###

        redis_pipeline.run_pipeline()

    def work_4_auotfix(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS_SLAVE-故障自愈"))
        """适用于 集群中Slave 故障自愈模型
        # # 探测故障实例状态 ## ## 修改元数据状态 ##
        # # 根据需要申请替换 ##
        步骤：   获取变更锁--> 新实例部署-->
                重建热备--> 检测同步状态-->
                Kill Dead链接--> 下架旧实例
        """
        # # ### 尝试修复故障实例 ######################################################################
        # sub_pipelines = []
        # for old_slave, new_slave in self.data["replace_relation"].items():
        #     params = {
        #         "ip": new_slave,
        #         "ports": act_kwargs.cluster["slave_ports"][old_slave],
        #         "wait_seconds": 600, "last_io_second_ago":10,
        #     }
        #     sub_builder = RedisLocalRepairAtomJob(self.root_id, self.data, act_kwargs, params)
        #     sub_pipelines.append(sub_builder)
        # redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
