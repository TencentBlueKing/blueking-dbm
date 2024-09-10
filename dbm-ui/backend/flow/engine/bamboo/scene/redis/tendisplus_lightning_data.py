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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_tendisplus_instance_type
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.tendisplus_lightning import TendisplusClusterLightningComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, TendisplusLightningContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import async_multi_clusters_precheck, lightning_cluster_nodes

logger = logging.getLogger("flow")


class TendisPlusLightningData(object):
    """
    Tendisplus Lightning 批量,快速导入数据
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        data = {
            "bk_biz_id":"",
            "ticket_type": "TENDISPLUS_LIGHTNING_DATA"
            "infos":[
                "cluster_id":1,
                "cos_file_keys": [
                    "xxxx",
                    "yyy"
                ]
            ]
        }
        """
        self.root_id = root_id
        self.data = data
        self.precheck(self.data["infos"])

    @staticmethod
    def precheck(infos: list):
        """
        @summary: 预检查
        """
        to_precheck_cluster_ids = set()
        for input_item in infos:
            # 如果重复,则报错
            if input_item["cluster_id"] in to_precheck_cluster_ids:
                raise Exception(
                    _("cluster_id:{}重复,同一个集群不能同时执行多个Tendisplus Lightning").format(input_item["cluster_id"])
                )
            to_precheck_cluster_ids.add(input_item["cluster_id"])
        # 并发检查多个cluster的proxy、redis实例状态
        async_multi_clusters_precheck(to_precheck_cluster_ids)
        # 检查集群类型 和 是否有running的slave
        for input_item in infos:
            cluster = Cluster.objects.get(id=input_item["cluster_id"])
            if not is_tendisplus_instance_type(cluster.cluster_type):
                raise Exception(
                    _("cluster_id:{} immute_domain:{} cluster_type:{} Tendisplus Lightning 仅支持Tendisplus集群").format(
                        cluster.id, cluster.immute_domain, cluster.cluster_type
                    )
                )
            # 确保每个master都有个running的slave
            lightning_cluster_nodes(input_item["cluster_id"])

    def lightning_data_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = TendisplusLightningContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        sub_pipelines = []

        for input_item in self.data["infos"]:
            cluster = Cluster.objects.get(id=input_item["cluster_id"])
            passwd_ret = PayloadHandler.redis_get_cluster_password(cluster)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            cluster_kwargs = deepcopy(act_kwargs)
            sub_pipeline.add_act(
                act_name=_("初始化配置-{}".format(cluster.immute_domain)),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(cluster_kwargs),
            )

            cluster_nodes = lightning_cluster_nodes(cluster.id)
            slave_ip_instance = defaultdict(list)
            slave_ips_set = set()
            master_slave_pairs = []
            for node in cluster_nodes:
                slave_ip, slave_port = node["slave_addr"].split(":")
                master_ip, master_port = node["master_addr"].split(":")
                slave_ips_set.add(slave_ip)
                slave_ip_instance[slave_ip].append({"ip": slave_ip, "port": int(slave_port)})
                master_slave_pairs.append(
                    {
                        "master": {"ip": master_ip, "port": int(master_port)},
                        "slave": {"ip": slave_ip, "port": int(slave_port)},
                    }
                )

            acts_list = []
            for ip in slave_ips_set:
                # 下发介质
                act_kwargs.exec_ip = ip
                acts_list.append(
                    {
                        "act_name": _("{}-下发介质包").format(ip),
                        "act_component_code": TransFileComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            if acts_list:
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 批量导入数据,并等待任务完成
            cluster_kwargs.cluster["cluster_id"] = cluster.id
            cluster_kwargs.cluster["cos_file_keys"] = input_item["cos_file_keys"]
            sub_pipeline.add_act(
                act_name=_("批量生成sst文件并导入"),
                act_component_code=TendisplusClusterLightningComponent.code,
                kwargs=asdict(cluster_kwargs),
            )

            # slave执行reshape
            acts_list = []
            for slave_ip, instances in slave_ip_instance.items():
                cluster_kwargs.exec_ip = slave_ip
                cluster_kwargs.cluster = {"instances": instances, "redis_password": passwd_ret.get("redis_password")}
                cluster_kwargs.get_redis_payload_func = RedisActPayload.tendisplus_reshape.__name__
                acts_list.append(
                    {
                        "act_name": _("执行reshape: {}").format(slave_ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(cluster_kwargs),
                    }
                )
            if acts_list:
                sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # slave执行cluster failover,slave会变成 new master
            slave_ips_list = list(slave_ips_set)
            cluster_kwargs.exec_ip = slave_ips_list[0]
            cluster_kwargs.cluster = {
                "redis_master_slave_pairs": master_slave_pairs,
                "redis_password": passwd_ret.get("redis_password"),
            }
            cluster_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_failover.__name__
            sub_pipeline.add_act(
                act_name=_("slave执行cluster failover"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(cluster_kwargs),
            )
            # 断开new_master->new_slave同步关系
            # old master(new slave)上执行 cluster reset + flushall + cluster meet
            reset_flush_meet_params = []
            for node in cluster_nodes:
                slave_ip, slave_port = node["slave_addr"].split(":")
                master_ip, master_port = node["master_addr"].split(":")
                reset_flush_meet_params.append(
                    {
                        "reset_ip": master_ip,
                        "reset_port": int(master_port),
                        "reset_redis_password": passwd_ret.get("redis_password"),
                        "meet_ip": slave_ip,
                        "meet_port": int(slave_port),
                        "do_flushall": True,
                        "do_cluster_meet": True,
                    }
                )
            cluster_kwargs.exec_ip = slave_ips_list[0]
            cluster_kwargs.cluster = {"reset_flush_meet_params": reset_flush_meet_params}
            cluster_kwargs.get_redis_payload_func = RedisActPayload.redis_clsuter_reset_flush_meet.__name__
            sub_pipeline.add_act(
                act_name=_("new_master->new_slave断开同步关系"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(cluster_kwargs),
            )
            # 重建同步关系
            replica_pairs_params = []
            for node in cluster_nodes:
                slave_ip, slave_port = node["slave_addr"].split(":")
                master_ip, master_port = node["master_addr"].split(":")
                replica_pairs_params.append(
                    {
                        "master_ip": slave_ip,
                        "master_port": int(slave_port),
                        "master_auth": passwd_ret.get("redis_password"),
                        "slave_ip": master_ip,
                        "slave_port": int(master_port),
                        "slave_password": passwd_ret.get("redis_password"),
                    }
                )
            cluster_kwargs.exec_ip = slave_ips_list[0]
            cluster_kwargs.cluster = {"replica_pairs": replica_pairs_params}
            cluster_kwargs.get_redis_payload_func = RedisActPayload.redis_init_batch_replicate.__name__
            sub_pipeline.add_act(
                act_name=_("new_master->new_slave重建同步关系"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(cluster_kwargs),
            )

            # 更新元数据
            switch_master_slave_pairs = {"cluster_id": cluster.id, "replication_pairs": []}
            for node in cluster_nodes:
                slave_ip, slave_port = node["slave_addr"].split(":")
                master_ip, master_port = node["master_addr"].split(":")
                switch_master_slave_pairs["replication_pairs"].append(
                    {
                        "master_ip": master_ip,
                        "master_port": int(master_port),
                        "slave_ip": slave_ip,
                        "slave_port": int(slave_port),
                    }
                )
            cluster_kwargs.cluster["meta_func_name"] = RedisDBMeta.swith_master_slave_for_cluster_faiover.__name__
            cluster_kwargs.cluster["switch_master_slave_pairs"] = switch_master_slave_pairs
            sub_pipeline.add_act(
                act_name=_("元数据更新"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(cluster_kwargs),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("集群{}批量导入数据").format(cluster.immute_domain))
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
