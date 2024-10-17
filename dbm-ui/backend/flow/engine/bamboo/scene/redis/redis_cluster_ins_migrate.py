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
from backend.db_meta.enums import ClusterEntryRole, ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_redis_cluster_protocal
from backend.flow.consts import (
    DEFAULT_LAST_IO_SECOND_AGO,
    DEFAULT_MASTER_DIFF_TIME,
    DEFAULT_REDIS_START_PORT,
    DnsOpType,
    SyncType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    AccessManagerAtomJob,
    ClusterPredixyConfigServersRewriteAtomJob,
    RedisBatchInstallAtomJob,
    RedisBatchShutdownAtomJob,
    RedisClusterSwitchAtomJob,
    RedisMakeSyncAtomJob,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisClusterInsMigrateFlow(object):
    """
    redis集群选定实例迁移

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
        """
        获取集群相关的信息
        - proxy_ips/proxy_port/cluster_type/实例映射关系
        """
        ins_link_dict = {}
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            master_ins = "{}:{}".format(master_obj.machine.ip, master_obj.port)
            slave_obj = master_obj.as_ejector.get().receiver
            slave_ins = "{}:{}".format(slave_obj.machine.ip, slave_obj.port)
            ins_link_dict[master_ins] = slave_ins

        return {
            "cluster_type": cluster.cluster_type,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_name": cluster.name,
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "proxy_port": cluster.proxyinstance_set.all()[0].port,
            "ins_link_dict": ins_link_dict,
            "immute_domain": cluster.immute_domain,
            "db_version": cluster.major_version,
        }

    def __init_builder(self, operate_name: str, info: dict):
        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], info["cluster_id"])
        sync_type = SyncType.SYNC_MMS  # ssd sync from master
        if cluster_info["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            sync_type = SyncType.SYNC_SMS

        flow_data = {**info, **self.data}
        for k, v in cluster_info.items():
            flow_data[k] = v
        sub_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **cluster_info,
            "operate": operate_name,
            "sync_type": sync_type,
            "bk_biz_id": self.data["bk_biz_id"],
        }
        act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
        logger.info("+===+++++===current tick_data info+++++===++++ :: {}".format(act_kwargs))

        sub_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        return sub_pipeline, act_kwargs

    def generate_install_ins(self, info) -> dict:
        new_master_ports = {}
        new_host_repl = {}
        machine_spec_dict = {}
        for migrate_info in info["migrate_list"]:
            master_ip = migrate_info["dest_master"]
            slave_ip = migrate_info["dest_slave"]
            if master_ip not in new_master_ports:
                new_master_ports[master_ip] = [DEFAULT_REDIS_START_PORT]
                new_host_repl[master_ip] = slave_ip
                machine_spec_dict[master_ip] = migrate_info["resource_spec"]["master"]
                machine_spec_dict[slave_ip] = migrate_info["resource_spec"]["slave"]
            else:
                new_master_ports[master_ip].append(new_master_ports[master_ip][-1] + 1)

        return {
            "new_master_ports": new_master_ports,
            "new_host_repl": new_host_repl,
            "machine_spec_dict": machine_spec_dict,
        }

    def get_redis_install_sub_pipelines(self, act_kwargs, info) -> list:
        """
        新机器安装实例子流程
        """
        install_redis_sub_pipeline = []
        install_redis_params = self.generate_install_ins(info)
        for master_ip, ports in install_redis_params["new_master_ports"].items():
            act_kwargs.exec_ip = master_ip
            install_master_redis_params = {
                "meta_role": InstanceRole.REDIS_MASTER.value,
                "start_port": DEFAULT_REDIS_START_PORT,
                "ip": master_ip,
                "ports": ports,
                "instance_numb": len(ports),
                "spec_id": install_redis_params["machine_spec_dict"][master_ip]["id"],
                "spec_config": install_redis_params["machine_spec_dict"][master_ip],
            }
            install_redis_sub_pipeline.append(
                RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, install_master_redis_params)
            )

            slave_ip = install_redis_params["new_host_repl"][master_ip]
            act_kwargs.exec_ip = slave_ip
            install_slave_redis_params = {
                "meta_role": InstanceRole.REDIS_SLAVE.value,
                "start_port": DEFAULT_REDIS_START_PORT,
                "ip": slave_ip,
                "ports": ports,
                "instance_numb": len(ports),
                "spec_id": install_redis_params["machine_spec_dict"][slave_ip]["id"],
                "spec_config": install_redis_params["machine_spec_dict"][slave_ip],
            }
            install_redis_sub_pipeline.append(
                RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, install_slave_redis_params)
            )

        return install_redis_sub_pipeline

    def generate_sync_relation(self, act_kwargs, info, is_rediscluster=False) -> list:
        new_master_ports = {}
        new_repl = {}
        old_repl = {}
        sync_relations = []
        # new_master可能不是相邻顺序，所以需要暂存一下，最终再复制给sync_relations的ins_link
        ins_link_list = defaultdict(list)
        for migrate_info in info["migrate_list"]:
            old_master_ins = migrate_info["src_master"]
            new_master_ip = migrate_info["dest_master"]
            new_slave_ip = migrate_info["dest_slave"]
            if new_master_ip not in new_master_ports:
                new_master_ports[new_master_ip] = DEFAULT_REDIS_START_PORT
            else:
                new_master_ports[new_master_ip] += 1

            # 计算sync相关信息
            old_slave_ins = act_kwargs.cluster["ins_link_dict"][old_master_ins]
            old_master_ip = old_master_ins.split(IP_PORT_DIVIDER)[0]
            old_slave_ip = old_slave_ins.split(IP_PORT_DIVIDER)[0]
            old_master_port = old_master_ins.split(IP_PORT_DIVIDER)[1]
            old_slave_port = old_slave_ins.split(IP_PORT_DIVIDER)[1]
            new_repl[new_master_ip] = new_slave_ip
            old_repl[old_master_ip] = old_slave_ip
            ins_link_list["{}-{}".format(new_master_ip, old_master_ip)].append(
                {
                    "origin_1": int(old_master_port),
                    "origin_2": int(old_slave_port),
                    "sync_dst1": new_master_ports[new_master_ip],
                    "sync_dst2": new_master_ports[new_master_ip],
                }
            )

        for sync_info, ins_link in ins_link_list.items():
            new_master_ip = sync_info.split("-")[0]
            new_slave_ip = new_repl[new_master_ip]
            if is_rediscluster:
                new_master_ip = new_slave_ip
            old_master_ip = sync_info.split("-")[1]
            old_slave_ip = old_repl[old_master_ip]
            sync_relations.append(
                {
                    "sync_type": act_kwargs.cluster["sync_type"],
                    "origin_1": old_master_ip,
                    "origin_2": old_slave_ip,
                    "sync_dst1": new_master_ip,
                    "sync_dst2": new_slave_ip,
                    "ins_link": ins_link,
                }
            )
        return sync_relations

    def generate_shutdown_ins(self, act_kwargs, info) -> dict:
        """
        master和slave机器上的端口可能不一致，需要计算slave上的ports
        计算老机器需要下架的实例列表。
        """
        shutdown_ip_ports_map = defaultdict(list)
        shutdown_ignore_ips_map = defaultdict(list)
        for migrate_info in info["migrate_list"]:
            old_master_ins = migrate_info["src_master"]
            old_slave_ins = act_kwargs.cluster["ins_link_dict"][old_master_ins]

            shutdown_master_ip = old_master_ins.split(IP_PORT_DIVIDER)[0]
            shutdown_master_port = int(old_master_ins.split(IP_PORT_DIVIDER)[1])
            shutdown_slave_ip = old_slave_ins.split(IP_PORT_DIVIDER)[0]
            shutdown_slave_port = int(old_slave_ins.split(IP_PORT_DIVIDER)[1])

            shutdown_ip_ports_map[shutdown_master_ip].append(shutdown_master_port)
            shutdown_ip_ports_map[shutdown_slave_ip].append(shutdown_slave_port)

            shutdown_ignore_ips_map[shutdown_master_ip].append(shutdown_slave_ip)
            shutdown_ignore_ips_map[shutdown_slave_ip].append(shutdown_master_ip)

        for k, v in shutdown_ignore_ips_map.items():
            shutdown_ignore_ips_map[k] = list(set(v))
        return {
            "shutdown_ip_ports_map": dict(shutdown_ip_ports_map),
            "shutdown_ignore_ips_map": dict(shutdown_ignore_ips_map),
        }

    def redis_cluster_ins_migrate_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            # 初始化参数
            new_master_ips, new_slave_ips = [], []
            for migrate_info in info["migrate_list"]:
                new_master_ips.append(migrate_info["dest_master"])
                new_slave_ips.append(migrate_info["dest_slave"])
            new_master_ips = list(set(new_master_ips))
            new_slave_ips = list(set(new_slave_ips))
            sub_pipeline, act_kwargs = self.__init_builder(_("Redis集群指定实例迁移"), info)
            # 安装redis
            sub_pipeline.add_parallel_sub_pipeline(self.get_redis_install_sub_pipelines(act_kwargs, info))

            # 建立主从同步
            # 计算同步参数
            sync_relations = self.generate_sync_relation(act_kwargs, info)
            redis_sync_sub_pipelines = []
            for sync_params in sync_relations:
                sub_builder = RedisMakeSyncAtomJob(self.root_id, self.data, act_kwargs, sync_params)
                redis_sync_sub_pipelines.append(sub_builder)
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=redis_sync_sub_pipelines)

            shutdown_info = self.generate_shutdown_ins(act_kwargs, info)
            shutdown_ip_ports = shutdown_info["shutdown_ip_ports_map"]
            shutdown_ignore_ips = shutdown_info["shutdown_ignore_ips_map"]
            if is_redis_cluster_protocal(act_kwargs.cluster["cluster_type"]):
                sync_relations2 = self.generate_sync_relation(act_kwargs, info, is_rediscluster=True)

                redis_sync_sub_pipelines = []
                for sync_params in sync_relations2:
                    sub_builder = RedisMakeSyncAtomJob(self.root_id, self.data, act_kwargs, sync_params)
                    redis_sync_sub_pipelines.append(sub_builder)
                sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=redis_sync_sub_pipelines)

                # 如果是rediscluster协议集群。并且迁移的是30000实例，域名和clb这些信息需要同步删除
                acts_list = []
                for ip, ports in shutdown_ip_ports.items():
                    if DEFAULT_REDIS_START_PORT in ports:
                        params = {
                            "cluster_id": info["cluster_id"],
                            "port": DEFAULT_REDIS_START_PORT,
                            "del_ips": ip,
                            "op_type": DnsOpType.RECYCLE_RECORD,
                        }
                        access_sub_builder = AccessManagerAtomJob(self.root_id, self.data, act_kwargs, params)
                        if access_sub_builder is not None:
                            acts_list.append(access_sub_builder)
                sub_pipeline.add_parallel_sub_pipeline(acts_list)

            # 切换
            act_kwargs.cluster["cluster_id"] = info["cluster_id"]
            act_kwargs.cluster["switch_condition"] = {
                "is_check_sync": True,  # 不强制切换
                "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
                "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
                "can_write_before_switch": True,
                "sync_type": act_kwargs.cluster["sync_type"],
            }
            sub_builder = RedisClusterSwitchAtomJob(self.root_id, self.data, act_kwargs, sync_relations)
            sub_pipeline.add_sub_pipeline(sub_flow=sub_builder)

            # 如果是rediscluster协议集群，需要增加nodes域名. 默认指定集群扩容都是已有nodes域名的集群
            if is_redis_cluster_protocal(act_kwargs.cluster["cluster_type"]):
                act_kwargs.cluster["nodes_domain"] = "nodes." + act_kwargs.cluster["immute_domain"]
                act_kwargs.cluster["meta_func_name"] = RedisDBMeta.update_cluster_entry.__name__
                sub_pipeline.add_act(
                    act_name=_("更新storageinstance_bind_entry元数据"),
                    act_component_code=RedisDBMetaComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 增加nodes域名
                params = {
                    "cluster_id": info["cluster_id"],
                    "port": DEFAULT_REDIS_START_PORT,
                    "add_ips": new_master_ips + new_slave_ips,
                    "op_type": DnsOpType.CREATE,
                    "role": [ClusterEntryRole.NODE_ENTRY.value],
                }
                access_sub_builder = AccessManagerAtomJob(self.root_id, self.data, act_kwargs, params)
                sub_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)

            sub_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})

            # 下架老实例
            redis_shutdown_sub_pipelines = []
            act_kwargs.cluster["created_by"] = self.data["created_by"]
            for ip, ports in shutdown_ip_ports.items():
                params = {"ip": ip, "ports": ports, "ignore_ips": shutdown_ignore_ips[ip], "force_shutdown": False}
                redis_shutdown_sub_pipelines.append(
                    RedisBatchShutdownAtomJob(self.root_id, self.data, act_kwargs, params)
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=redis_shutdown_sub_pipelines)
            # 新老机器刷新dbmon
            acts_list = []
            for ip, ports in shutdown_ip_ports.items():
                act_kwargs.exec_ip = ip
                act_kwargs.cluster["ip"] = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
                acts_list.append(
                    {
                        "act_name": _("{}-重装bkdbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            for ip in new_master_ips + new_slave_ips:
                act_kwargs.exec_ip = ip
                act_kwargs.cluster["ip"] = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
                acts_list.append(
                    {
                        "act_name": _("{}-重装bkdbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list)
            # 重写predixy配置文件
            if is_redis_cluster_protocal(act_kwargs.cluster["cluster_type"]):
                # 重写predixy配置文件
                predixy_conf_rewrite_bulider = ClusterPredixyConfigServersRewriteAtomJob(
                    self.root_id,
                    self.data,
                    act_kwargs,
                    {"cluster_domain": act_kwargs.cluster["immute_domain"], "to_remove_servers": []},
                )
                if predixy_conf_rewrite_bulider:
                    sub_pipeline.add_sub_pipeline(predixy_conf_rewrite_bulider)

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("{}指定实例迁移").format(act_kwargs.cluster["immute_domain"]))
            )

        redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)
        redis_pipeline.run_pipeline()
