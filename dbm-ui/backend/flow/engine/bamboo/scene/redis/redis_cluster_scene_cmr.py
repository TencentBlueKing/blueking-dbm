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
from backend.flow.consts import SyncType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisClusterMasterReplaceJob, RedisClusterSlaveReplaceJob
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisClusterCMRSceneFlow(object):
    """
    Complete machine replacement

    #### Master 会执行成对替换
    #### 替换顺序： 优先Slave,然后Proxy,最后Master
    #### 最后会生成 proxy下架单/集群切换单据
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"vitox",
        "ticket_type":"REDIS_CLUSTER_CUTOFF",
        "infos": [
            {
              "cluster_id": 1,
              "redis_proxy": {
                  "1.1.1.a":"1.1.1.b",
                  "1.1.1.c":"1.1.1.d"
              }
              "redis_slave": {
                  "1.1.f.1":"1.1.g.2",
                  "1.1.e.3":"1.1.h.4"
              }
              "redis_master": {
                  "1.i.1.1":["1.1.k.2(master)", "1.m.1.3(slave)"],
                  "1.1.j.3":["1.l.1.2(master)", "1.1.o.3(slave)"]
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

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群现有信息
        1. master 对应 slave 机器
        2. master 上的端口列表
        3. 实例对应关系：{master:port:slave:port}
        """
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        master_ports, slave_ports = defaultdict(list), defaultdict(list)
        ins_pair_map, slave_ins_map = defaultdict(), defaultdict()
        master_slave_map, slave_master_map = defaultdict(), defaultdict()

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
            "cluster_id": cluster.id,
            "slave_ports": dict(slave_ports),
            "master_ports": dict(master_ports),
            "ins_pair_map": dict(ins_pair_map),
            "slave_ins_map": dict(slave_ins_map),
            "slave_master_map": dict(slave_master_map),
            "master_slave_map": dict(master_slave_map),
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "db_version": cluster.major_version,
        }

    def __init_builder(self, operate_name: str):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = False
        act_kwargs.cluster = {
            "operate": operate_name,
        }
        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        return redis_pipeline, act_kwargs

    # 这里整理替换所需要的参数
    def complete_machine_replace(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS-整机替换"))
        sub_pipelines = []
        for cluster_replacement in self.data["infos"]:
            cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], self.data["cluster_id"])
            sync_type = SyncType.SYNC_MMS  # ssd sync from master
            if cluster_info["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
                sync_type = SyncType.SYNC_SMS

            flow_data = self.data
            for k, v in cluster_info.items():
                # flow_data[k] = v
                act_kwargs.cluster[k] = v
            flow_data["sync_type"] = sync_type
            flow_data["replace_info"] = cluster_replacement
            sub_pipeline = self.generate_cluster_replacement(flow_data, act_kwargs, cluster_replacement)
            sub_pipelines.append(sub_pipeline)

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        return redis_pipeline.run_pipeline()

    # 组装&控制 集群替换流程
    def generate_cluster_replacement(self, flow_data, act_kwargs, replacement_param):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)

        # 先添加Slave替换流程
        if replacement_param.get("redis_slave"):
            sub_pipeline.add_sub_pipeline()

        # 再添加Proxy替换流程
        if replacement_param.get("redis_proxy"):
            slave_replace_pipe = RedisClusterSlaveReplaceJob(
                self.root_id, flow_data, act_kwargs, replacement_param.get("redis_slave")
            )
            sub_pipeline.add_sub_pipeline(slave_replace_pipe)

        # 最后添加Master替换流程
        if replacement_param.get("redis_master"):
            master_replace_pipe = RedisClusterMasterReplaceJob(
                self.root_id, flow_data, act_kwargs, replacement_param.get("redis_master")
            )
            sub_pipeline.add_sub_pipeline(master_replace_pipe)

        return sub_pipeline.build_sub_process(sub_name=_("Redis-{}-整机替换").format(act_kwargs["immute_domain"]))
