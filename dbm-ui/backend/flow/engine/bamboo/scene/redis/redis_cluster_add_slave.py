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
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_REDIS_START_PORT, SyncType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ClusterPredixyConfigServersRewriteAtomJob
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_install import RedisBatchInstallAtomJob
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_makesync import RedisMakeSyncAtomJob
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_shutdown import RedisBatchShutdownAtomJob
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode, get_twemproxy_cluster_server_shards

logger = logging.getLogger("flow")


class RedisClusterAddSlaveFlow(object):
    """
    redis集群添加slave
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        """
        self.root_id = root_id
        self.data = data
        self.precheck()

    def get_cluster_info(self, bk_biz_id, cluster_id):
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        master_ports, slave_ports = defaultdict(list), defaultdict(list)
        ins_pair_map, slave_ins_map = defaultdict(), defaultdict()
        master_slave_map, slave_master_map = defaultdict(), defaultdict()

        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            master_ports[master_obj.machine.ip].append(master_obj.port)
            if master_obj.as_ejector and master_obj.as_ejector.first():
                my_slave_obj = master_obj.as_ejector.get().receiver
                slave_ports[my_slave_obj.machine.ip].append(my_slave_obj.port)
                ins_pair_map[
                    "{}{}{}".format(master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port)
                ] = "{}{}{}".format(my_slave_obj.machine.ip, IP_PORT_DIVIDER, my_slave_obj.port)
                ifslave = master_slave_map.get(master_obj.machine.ip)
                if ifslave and ifslave != my_slave_obj.machine.ip:
                    raise Exception(
                        "unsupport mutil slave with cluster {} 4:{}".format(
                            cluster.immute_domain, master_obj.machine.ip
                        )
                    )
                else:
                    master_slave_map[master_obj.machine.ip] = my_slave_obj.machine.ip

                slave_ins_map[
                    "{}{}{}".format(my_slave_obj.machine.ip, IP_PORT_DIVIDER, my_slave_obj.port)
                ] = "{}{}{}".format(master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port)

                ifmaster = slave_master_map.get(my_slave_obj.machine.ip)
                if ifmaster and ifmaster != master_obj.machine.ip:
                    raise Exception(
                        "unsupport mutil master for cluster {}:{}".format(
                            cluster.immute_domain, my_slave_obj.machine.ip
                        )
                    )
                else:
                    slave_master_map[my_slave_obj.machine.ip] = master_obj.machine.ip
        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": str(cluster.bk_biz_id),
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "cluster_name": cluster.name,
            "cluster_id": cluster.id,
            "slave_ports": dict(slave_ports),
            "master_ports": dict(master_ports),
            "ins_pair_map": dict(ins_pair_map),
            "slave_ins_map": dict(slave_ins_map),
            "slave_master_map": dict(slave_master_map),
            "master_slave_map": dict(master_slave_map),
            "proxy_port": cluster.proxyinstance_set.first().port,
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "db_version": cluster.major_version,
        }

    def add_slave_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)

        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        bk_biz_id = self.data["bk_biz_id"]
        sub_pipelines = []
        for input_item in self.data["infos"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            cluster_kwargs = deepcopy(act_kwargs)
            cluster_info = self.get_cluster_info(bk_biz_id, input_item["cluster_id"])
            cluster_kwargs.cluster.update(cluster_info)
            cluster_kwargs.cluster["created_by"] = self.data["created_by"]

            newslave_to_master = {}
            for host_pair in input_item["pairs"]:
                master_ip = host_pair["redis_master"]["ip"]
                for new_slave_item in host_pair["redis_slave"]:
                    for port in cluster_info["master_ports"][master_ip]:
                        newslave_to_master[
                            "{}{}{}".format(new_slave_item["ip"], IP_PORT_DIVIDER, port)
                        ] = "{}{}{}".format(master_ip, IP_PORT_DIVIDER, port)

            twemproxy_server_shards = get_twemproxy_cluster_server_shards(
                bk_biz_id, input_item["cluster_id"], newslave_to_master
            )

            sub_pipeline.add_act(
                act_name=_("初始化配置-{}".format(cluster_info["immute_domain"])),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(cluster_kwargs),
            )
            child_pipelines = []
            for host_pair in input_item["pairs"]:
                master_ip = host_pair["redis_master"]["ip"]
                for new_slave_item in host_pair["redis_slave"]:
                    install_builder = RedisBatchInstallAtomJob(
                        root_id=self.root_id,
                        ticket_data=self.data,
                        sub_kwargs=cluster_kwargs,
                        param={
                            "ip": new_slave_item["ip"],
                            "meta_role": InstanceRole.REDIS_SLAVE.value,
                            "start_port": DEFAULT_REDIS_START_PORT,
                            "ports": cluster_info["master_ports"][master_ip],
                            "instance_numb": len(cluster_info["master_ports"][master_ip]),
                            "spec_id": input_item["resource_spec"][master_ip].get("id", 0),
                            "spec_config": input_item["resource_spec"][master_ip],
                            "server_shards": twemproxy_server_shards.get(new_slave_item["ip"], {}),
                            "cache_backup_mode": get_cache_backup_mode(bk_biz_id, input_item["cluster_id"]),
                        },
                    )
                    child_pipelines.append(install_builder)
            sub_pipeline.add_parallel_sub_pipeline(child_pipelines)

            child_pipelines = []
            for host_pair in input_item["pairs"]:
                master_ip = host_pair["redis_master"]["ip"]
                for new_slave_item in host_pair["redis_slave"]:
                    sync_param = {
                        "sync_type": SyncType.SYNC_MS,
                        "origin_1": master_ip,
                        "sync_dst1": new_slave_item["ip"],
                        "ins_link": [],
                        "server_shards": twemproxy_server_shards.get(new_slave_item["ip"], {}),
                        "cache_backup_mode": get_cache_backup_mode(bk_biz_id, input_item["cluster_id"]),
                    }
                    for port in cluster_info["master_ports"][master_ip]:
                        sync_param["ins_link"].append({"origin_1": str(port), "sync_dst1": str(port)})
                    sync_builder = RedisMakeSyncAtomJob(
                        root_id=self.root_id, ticket_data=self.data, sub_kwargs=cluster_kwargs, params=sync_param
                    )
                    child_pipelines.append(sync_builder)
            sub_pipeline.add_parallel_sub_pipeline(child_pipelines)

            # 新节点加入集群 ################################################################################
            cluster_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_redo_slaves.__name__
            cluster_kwargs.cluster["old_slaves"] = []
            cluster_kwargs.cluster["created_by"] = self.data["created_by"]
            cluster_kwargs.cluster["tendiss"] = []
            child_pipelines = []
            for host_pair in input_item["pairs"]:
                master_ip = host_pair["redis_master"]["ip"]
                old_slave_ip = cluster_info["master_slave_map"].get(master_ip)
                if old_slave_ip:
                    old_slave_ports = cluster_info["slave_ports"][old_slave_ip]
                    cluster_kwargs.cluster["old_slaves"].append({"ip": old_slave_ip, "ports": old_slave_ports})
                for new_slave_item in host_pair["redis_slave"]:
                    for port in cluster_info["master_ports"][master_ip]:
                        cluster_kwargs.cluster["tendiss"].append(
                            {
                                "ejector": {
                                    "ip": master_ip,
                                    "port": port,
                                },
                                "receiver": {"ip": new_slave_item["ip"], "port": port},
                            }
                        )
            sub_pipeline.add_act(
                act_name=_("Redis-新节点加入集群"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(cluster_kwargs),
            )

            # #### 下架旧实例 ############################################################################
            child_pipelines = []
            for host_pair in input_item["pairs"]:
                master_ip = host_pair["redis_master"]["ip"]
                old_slave_ip = cluster_info["master_slave_map"].get(master_ip)
                if old_slave_ip:
                    old_slave_ports = cluster_info["slave_ports"][old_slave_ip]
                    shutdown_builder = RedisBatchShutdownAtomJob(
                        self.root_id,
                        self.data,
                        cluster_kwargs,
                        {
                            "ignore_ips": [],
                            "ip": old_slave_ip,
                            "ports": old_slave_ports,
                            "force_shutdown": True,
                        },
                    )
                    child_pipelines.append(shutdown_builder)
            if child_pipelines:
                sub_pipeline.add_parallel_sub_pipeline(child_pipelines)

            predixy_conf_rewrite_bulider = ClusterPredixyConfigServersRewriteAtomJob(
                self.root_id,
                self.data,
                act_kwargs,
                {"cluster_domain": cluster_info["immute_domain"], "to_remove_servers": []},
            )
            if predixy_conf_rewrite_bulider:
                sub_pipeline.add_sub_pipeline(predixy_conf_rewrite_bulider)

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("Redis-{}-新建从库").format(cluster_info["immute_domain"]))
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        return redis_pipeline.run_pipeline()

    def precheck(self):
        """
        a. 检查集群是否存在
        b. 检查集群中主节点是否存在
        c. 检查主节点是否有running的从节点
        """
        bk_biz_id = self.data["bk_biz_id"]
        for input_item in self.data["infos"]:
            try:
                cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=input_item["cluster_id"])
            except Cluster.DoesNotExist:
                raise Exception("redis cluster {} does not exist".format(input_item["cluster_id"]))

            for host_pair in input_item["pairs"]:
                master_insts = cluster.storageinstance_set.filter(
                    machine__ip=host_pair["redis_master"]["ip"], instance_role=InstanceRole.REDIS_MASTER.value
                )
                if not master_insts:
                    raise Exception(
                        "master {} does not exist in cluster {}".format(
                            host_pair["redis_master"]["ip"], cluster.immute_domain
                        )
                    )
                running_slaves_cnt = 0
                for master_obj in master_insts:
                    # running的slave 个数与 master 个数不相同,则可以继续执行
                    # 换句话说:存在redis_master 没有 slave 或者 某个slave不是 RUNNING状态,就能继续执行
                    if master_obj.as_ejector and master_obj.as_ejector.first():
                        slave_obj = master_obj.as_ejector.get().receiver
                        if slave_obj.status == InstanceStatus.RUNNING:
                            running_slaves_cnt += 1
                if running_slaves_cnt >= len(master_insts):
                    raise Exception(
                        "master({}) in cluster {} all instances has a running slave".format(
                            master_obj.machine.ip,
                            cluster.immute_domain,
                        )
                    )
