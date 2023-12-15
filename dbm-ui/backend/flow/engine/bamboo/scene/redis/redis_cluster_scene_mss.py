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
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import AppCache, Cluster, StorageInstance
from backend.flow.consts import DEFAULT_LAST_IO_SECOND_AGO, DEFAULT_MASTER_DIFF_TIME, SyncType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisClusterSwitchAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import (
    GetRedisActPayloadComponent,
    RedisActPayload,
)
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode, get_twemproxy_cluster_server_shards

logger = logging.getLogger("flow")


class RedisClusterMSSSceneFlow(object):
    """
    Master Slave Switch

    ### 把Slave提升为Master
    #### 1. 正常手动切换
    #### 2. 异常情况，强制切换 (1. 整机切换;2.部分切换)
    #### 3. 这里只做元数据层的 master/slave 对调,不对old master 下架
    {
        "bk_biz_id": 3,
        "uid": "2023051612120001",
        "created_by":"vitox",
        "ticket_type":"REDIS_CLUSTER_MASTER_FAILOVER",
        "force":false, # 是否需要强制切换
        "infos": [
            {
                "cluster_id": 1,
                "online_switch_type":"user_confirm/no_confirm",
                "pairs": [
                    {"redis_master": "1.1.a.3", "redis_slave": "1.1.2.b"}
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

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群现有信息
        1. master 对应 slave 机器
        2. master 上的端口列表
        3. 实例对应关系：{master:port:slave:port}
        """
        slave_ins_map, master_pair_map, master_slave_map, master_ports = (
            defaultdict(),
            defaultdict(),
            defaultdict(),
            defaultdict(list),
        )
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            master_ports[master_obj.machine.ip].append(master_obj.port)
            master_pair_map[
                "{}{}{}".format(master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port)
            ] = "{}{}{}".format(slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port)

            ifslave = master_slave_map.get(master_obj.machine.ip)
            if ifslave and ifslave != slave_obj.machine.ip:
                raise Exception(
                    "unsupport mutil slave with cluster {} 4:{}".format(cluster.immute_domain, master_obj.machine.ip)
                )

            slave_ins_map["{}{}{}".format(slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port)] = "{}{}{}".format(
                master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port
            )
            master_slave_map[master_obj.machine.ip] = slave_obj.machine.ip

        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "cluster_name": cluster.name,
            "cluster_id": cluster.id,
            "master_ports": dict(master_ports),
            "slave_ins_map": dict(slave_ins_map),
            "master_pair_map": dict(master_pair_map),
            "master_slave_map": dict(master_slave_map),
            "proxy_port": cluster.proxyinstance_set.first().port,
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "db_version": cluster.major_version,
        }

    def __init_builder(self, operate_name: str):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            "operate": operate_name,
        }
        return redis_pipeline, act_kwargs

    # 执行 正常/异常 情况下主从切换逻辑
    def redis_ms_switch(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS-主从切换"))
        sub_pipelines = []
        force_switch = self.data.get("force", False)
        for ms_switch in self.data["infos"]:
            cluster_kwargs = deepcopy(act_kwargs)
            cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], ms_switch["cluster_id"])

            flow_data = self.data
            for k, v in cluster_info.items():
                cluster_kwargs.cluster[k] = v
            cluster_kwargs.cluster["created_by"] = self.data["created_by"]
            cluster_kwargs.cluster["switch_option"] = ms_switch["online_switch_type"]
            flow_data["switch_input"] = ms_switch
            redis_pipeline.add_act(
                act_name=_("初始化配置-{}".format(cluster_info["immute_domain"])),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(cluster_kwargs),
            )
            sub_pipeline = self.generate_ms_switch_flow(flow_data, cluster_kwargs, ms_switch, force_switch)
            sub_pipelines.append(sub_pipeline)

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        return redis_pipeline.run_pipeline()

    # 组装&控制 集群切换流程
    def generate_ms_switch_flow(self, flow_data, act_kwargs, ms_switch, force=False):
        """
        1. 切换前同步检查
        2. 执行切换 3. 切换backends校验
        4. 刷新 new master 监控
        5. 元数据修改 old-master 2 unavliable.
        """
        redis_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)
        twemproxy_server_shards = get_twemproxy_cluster_server_shards(
            act_kwargs.cluster["bk_biz_id"], act_kwargs.cluster["cluster_id"], act_kwargs.cluster["slave_ins_map"]
        )

        sync_relations, master_ips, slave_ips = [], [], []
        for ms_pair in ms_switch["pairs"]:
            master_ip = ms_pair.get("redis_master", "why.no.ip.input")
            slave_ip = ms_pair.get("redis_slave", "why.no.ip.input")
            master_ips.append(master_ip)
            slave_ips.append(slave_ip)
            sync_params = {
                "origin_1": master_ip,
                "origin_2": slave_ip,
                "sync_dst1": slave_ip,
                "sync_dst2": slave_ip,
                "ins_link": [],
            }
            for master_port in act_kwargs.cluster["master_ports"][master_ip]:
                master_addr = "{}{}{}".format(master_ip, IP_PORT_DIVIDER, master_port)
                slave_addr = act_kwargs.cluster["master_pair_map"][master_addr]
                slave_port = slave_addr.split(IP_PORT_DIVIDER)[1]
                sync_params["ins_link"].append(
                    {
                        "origin_1": int(master_port),
                        "origin_2": int(slave_port),
                        "sync_dst1": int(slave_port),
                        "sync_dst2": int(slave_port),
                    }
                )
            sync_relations.append(sync_params)

        # 重新下发介质 ###################################################################################
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs.file_list = trans_files.redis_cluster_apply_proxy(act_kwargs.cluster["cluster_type"])
        act_kwargs.exec_ip = master_ips + slave_ips
        redis_pipeline.add_act(
            act_name=_("{}-下发介质包").format(master_ips + slave_ips),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 重新下发介质 ###################################################################################

        # 执行切换 #####################################################################################
        act_kwargs.cluster["switch_condition"] = {
            "sync_type": SyncType.SYNC_MS.value,
            "is_check_sync": force,  # 强制切换
            "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
            "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
            "can_write_before_switch": True,
        }
        sub_pipeline = RedisClusterSwitchAtomJob(self.root_id, flow_data, act_kwargs, sync_relations)
        redis_pipeline.add_sub_pipeline(sub_flow=sub_pipeline)
        # 执行切换 ###########################################################################完成######

        # 元数据修改 ###################################################################################
        sub_acts = []
        for master_ip in master_ips:
            sub_kwargs = deepcopy(act_kwargs)
            sub_kwargs.cluster["meta_update_ip"] = master_ip
            sub_kwargs.cluster["meta_update_ports"] = act_kwargs.cluster["master_ports"][master_ip]
            sub_kwargs.cluster["meta_update_status"] = InstanceStatus.UNAVAILABLE.value
            sub_kwargs.cluster["meta_func_name"] = RedisDBMeta.instances_failover_4_scene.__name__
            sub_acts.append(
                {
                    "act_name": _("Redis-{}-元数据修改".format(master_ip)),
                    "act_component_code": RedisDBMetaComponent.code,
                    "kwargs": asdict(sub_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=sub_acts)
        # 元数据修改 ###########################################################################完成######

        # 刷新监控 #####################################################################################
        app = AppCache.get_app_attr(act_kwargs.cluster["bk_biz_id"], "db_app_abbr")
        app_name = AppCache.get_app_attr(act_kwargs.cluster["bk_biz_id"], "bk_biz_name")
        sub_acts = []
        act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
        for slave_ip in slave_ips:
            sub_kwargs = deepcopy(act_kwargs)
            sub_kwargs.exec_ip = slave_ip
            sub_kwargs.cluster["servers"] = [
                {
                    "app": app,
                    "app_name": app_name,
                    "bk_biz_id": str(act_kwargs.cluster["bk_biz_id"]),
                    "bk_cloud_id": int(act_kwargs.cluster["bk_cloud_id"]),
                    "server_ip": slave_ip,
                    "server_ports": [s_obj.port for s_obj in StorageInstance.objects.filter(machine__ip=slave_ip)],
                    "meta_role": InstanceRole.REDIS_MASTER.value,
                    "cluster_name": act_kwargs.cluster["cluster_name"],
                    "cluster_type": act_kwargs.cluster["cluster_type"],
                    "cluster_domain": act_kwargs.cluster["immute_domain"],
                    "server_shards": twemproxy_server_shards.get(slave_ip, {}),
                    "cache_backup_mode": get_cache_backup_mode(
                        act_kwargs.cluster["bk_biz_id"], act_kwargs.cluster["cluster_id"]
                    ),
                }
            ]
            sub_acts.append(
                {
                    "act_name": _("Redis-{}-刷新监控".format(slave_ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(sub_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=sub_acts)
        # 刷新监控 ###########################################################################完成######

        return redis_pipeline.build_sub_process(
            sub_name=_("Redis-{}-主从切换").format(act_kwargs.cluster["immute_domain"])
        )
