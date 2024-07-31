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
from backend.db_meta.enums import ClusterEntryRole, InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.db_services.redis.util import is_redis_cluster_protocal
from backend.flow.consts import (
    DEFAULT_LAST_IO_SECOND_AGO,
    DEFAULT_MASTER_DIFF_TIME,
    DEFAULT_REDIS_START_PORT,
    DnsOpType,
    RedisCapacityUpdateType,
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
from backend.flow.engine.bamboo.scene.redis.redis_slots_migrate_sub import (
    redis_migrate_slots_4_contraction,
    redis_rebalance_slots_4_expansion,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cluster_info_by_cluster_id

logger = logging.getLogger("flow")


class RedisBackendScaleFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __pre_check(self, bk_biz_id, cluster_id, master_ips, slave_ips, new_shard_num, group_num):
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        old_shard_num = len(cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value))
        ips = master_ips + slave_ips
        if len(set(ips)) != len(ips):
            raise Exception("have ip address has been used multiple times.")
        if len(master_ips) != len(slave_ips):
            raise Exception("master machine len != slave machine len.")
        if len(master_ips) != group_num:
            raise Exception("machine len != group_num.")
        if old_shard_num != new_shard_num:
            raise Exception("old_shard_num {} != new_shard_num {}.".format(old_shard_num, new_shard_num))
        # 2024-05 要求可以不用整除，允许机器上的实例有多有少
        # if new_shard_num % group_num != 0:
        #     raise Exception("shard_num ({}) % group_num ({}) != 0.".format(new_shard_num, group_num))
        m = Machine.objects.filter(ip__in=ips).values("ip")
        if len(m) != 0:
            raise Exception("[{}] is used.".format(m))

    @staticmethod
    def get_cluster_info(bk_biz_id: int, cluster_id: int, version: str) -> dict:
        """
        获取集群现有信息
        1. master对应的端口 {"x.x.x.1":[30000,30001]...}
        2. master、slave实例对应关系 {"x.x.x.1:30000":"x.x.x.2:30000"...}
        3. proxy实例列表 [x.x.x.3:50000...]
        4. master、slave机器对应关系
        """
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        master_ip_ports_map = defaultdict(list)
        ins_pair_map = defaultdict()
        master_slave_map = defaultdict()
        old_master_list = []
        old_slave_list = []
        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            master_ip_ports_map[master_obj.machine.ip].append(master_obj.port)
            ins_pair_map["{}:{}".format(master_obj.machine.ip, master_obj.port)] = "{}:{}".format(
                slave_obj.machine.ip, slave_obj.port
            )

            ifslave = master_slave_map.get(master_obj.machine.ip)
            if ifslave and ifslave != slave_obj.machine.ip:
                raise Exception(
                    "unsupport mutil slave with cluster {} 4:{}".format(cluster.immute_domain, master_obj.machine.ip)
                )

            master_slave_map[master_obj.machine.ip] = slave_obj.machine.ip
            old_master_list.append(master_obj.machine.ip)
            old_slave_list.append(slave_obj.machine.ip)
        return {
            "cluster_id": cluster.id,
            "immute_domain": cluster.immute_domain,
            "cluster_name": cluster.name,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "master_ip_ports_map": dict(master_ip_ports_map),
            "ins_pair_map": dict(ins_pair_map),
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "master_slave_map": dict(master_slave_map),
            "db_version": version or cluster.major_version,
            "origin_db_version": cluster.major_version,
            "cluster_shard_num": len(
                cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)
            ),
            "old_master_list": list(set(old_master_list)),
            "old_slave_list": list(set(old_slave_list)),
        }

    def __init_builder(self, operate_name: str, info: dict):
        cluster_info = self.get_cluster_info(self.data["bk_biz_id"], info["cluster_id"], info["db_version"])
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
        }
        act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
        logger.info("+===+++++===current tick_data info+++++===++++ :: {}".format(act_kwargs))

        sub_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )
        return sub_pipeline, act_kwargs

    def generate_sync_relation(self, act_kwargs, master_ips, slave_ips, ins_num, superfluous_ins_num) -> list:
        """
        计算新老实例对应关系
        可能一对多，也可能多对一
        """
        sync_relations = []
        new_port_offset = 0
        new_host_index = 0
        # 当前新机器需要安装的实例数
        current_ins_num = ins_num + 1 if new_host_index < superfluous_ins_num else ins_num
        sync_type = act_kwargs.cluster["sync_type"]
        for old_master, old_master_ports in act_kwargs.cluster["master_ip_ports_map"].items():
            # old_master 或者 new_master变化了就需要append后初始化
            ins_link = []
            old_slave = ""

            old_master_ports.sort()
            for old_master_port in old_master_ports:
                # 获取老slave的ip和端口。这里端口不一定跟老master一致
                old_master_ins = "{}:{}".format(old_master, old_master_port)
                old_slave_ins = act_kwargs.cluster["ins_pair_map"][old_master_ins]
                old_slave = old_slave_ins.split(IP_PORT_DIVIDER)[0]
                old_slave_port = old_slave_ins.split(IP_PORT_DIVIDER)[1]
                # 新部署的实例端口肯定一致
                new_port = DEFAULT_REDIS_START_PORT + new_port_offset
                ins_link.append(
                    {
                        "origin_1": int(old_master_port),
                        "origin_2": int(old_slave_port),
                        "sync_dst1": new_port,
                        "sync_dst2": new_port,
                    }
                )
                new_port_offset += 1

                if new_host_index >= len(master_ips):
                    raise Exception("origin cluster shard_num > new cluster shard_num. pleace use dts")

                # 如果达到了新机器需要部署的实例个数，下一个就要用新机器了。这个地方初始化一些参数
                if new_port_offset >= current_ins_num:
                    new_master = master_ips[new_host_index]
                    new_slave = slave_ips[new_host_index]
                    sync_relations.append(
                        {
                            "sync_type": sync_type,
                            "origin_1": old_master,
                            "origin_2": old_slave,
                            "sync_dst1": new_master,
                            "sync_dst2": new_slave,
                            "ins_link": ins_link,
                        }
                    )

                    ins_link = []
                    new_port_offset = 0
                    new_host_index += 1
                    current_ins_num = ins_num + 1 if new_host_index < superfluous_ins_num else ins_num

            # 遍历完老机器上的端口，如果ins_link里有数据，此时需要先处理一下
            if ins_link:
                new_master = master_ips[new_host_index]
                new_slave = slave_ips[new_host_index]
                sync_relations.append(
                    {
                        "sync_type": sync_type,
                        "origin_1": old_master,
                        "origin_2": old_slave,
                        "sync_dst1": new_master,
                        "sync_dst2": new_slave,
                        "ins_link": ins_link,
                    }
                )
        return sync_relations

    def generate_shutdown_ins(self, act_kwargs) -> dict:
        """
        master和slave机器上的端口可能不一致，需要计算slave上的ports
        """
        shutdown_ip_ports_map = defaultdict(list)
        for old_master, old_master_ports in act_kwargs.cluster["master_ip_ports_map"].items():
            for old_master_port in old_master_ports:
                old_master_ins = "{}:{}".format(old_master, old_master_port)
                old_slave_ins = act_kwargs.cluster["ins_pair_map"][old_master_ins]
                old_slave = old_slave_ins.split(IP_PORT_DIVIDER)[0]
                old_slave_port = old_slave_ins.split(IP_PORT_DIVIDER)[1]

                shutdown_ip_ports_map[old_master].append(int(old_master_port))
                shutdown_ip_ports_map[old_slave].append(int(old_slave_port))
        return dict(shutdown_ip_ports_map)

    def generate_shutdown_ignore_ips(self, act_kwargs) -> dict:
        """
        老master和slave的复制关系，忽略来源为slave的请求
        """
        shutdown_ignore_ips_map = defaultdict(list)
        for old_master, old_master_ports in act_kwargs.cluster["master_ip_ports_map"].items():
            for old_master_port in old_master_ports:
                old_master_ins = "{}:{}".format(old_master, old_master_port)
                old_slave_ins = act_kwargs.cluster["ins_pair_map"][old_master_ins]
                old_slave = old_slave_ins.split(IP_PORT_DIVIDER)[0]

                shutdown_ignore_ips_map[old_master].append(old_slave)
                shutdown_ignore_ips_map[old_slave].append(old_master)
        for k, v in shutdown_ignore_ips_map.items():
            shutdown_ignore_ips_map[k] = list(set(v))
        return dict(shutdown_ignore_ips_map)

    def tendisplus_shards_update_and_keep_machine_flow(self, info) -> SubBuilder:
        """
        tendisplus集群 分片数变化了,原地变更 流程
        """
        new_cluster_info = get_cluster_info_by_cluster_id(cluster_id=info["cluster_id"])
        new_info = {
            "cluster_id": new_cluster_info["cluster_id"],
            "bk_cloud_id": new_cluster_info["bk_cloud_id"],
            "current_group_num": len(new_cluster_info["master_ips"]),
            "target_group_num": info["group_num"],
            "resource_spec": {"redis": new_cluster_info["redis_spec_config"]},
        }
        new_ip_group = []
        for group_info in info["backend_group"]:
            new_ip_group.append({"master": group_info["master"]["ip"], "slave": group_info["slave"]["ip"]})
        new_info["new_ip_group"] = new_ip_group
        logger.info("tendisplus_shards_update_and_keep_machine_flow new_info:{}".format(new_info))
        sub_pipeline = None
        if new_info["target_group_num"] > new_info["current_group_num"]:
            # 扩容
            sub_pipeline = redis_rebalance_slots_4_expansion(self.root_id, self.data, None, new_info)
        elif new_info["target_group_num"] < new_info["current_group_num"]:
            # 缩容
            new_info["is_delete_node"] = True
            sub_pipeline = redis_migrate_slots_4_contraction(self.root_id, self.data, None, new_info)
        return sub_pipeline

    def redis_backend_scale_flow(self):
        """
        redis 扩缩容流程：
            实例上架->新实例主从关系 -> 同步数据 -> 切换 -> 实例下架
            需要注意： 这里得new_master/new_slave可以相同。需要提前处理一下
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            cluster_info = self.get_cluster_info(self.data["bk_biz_id"], info["cluster_id"], info["db_version"])
            if (
                cluster_info["cluster_shard_num"] != info["shard_num"]
                and cluster_info["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster
                and info["update_mode"] == RedisCapacityUpdateType.KEEP_CURRENT_MACHINES
            ):
                # 对于tendisplus集群，分片数变化了,且为原地变更,需要单独处理
                sub_pipeline = self.tendisplus_shards_update_and_keep_machine_flow(info)
                sub_pipelines.append(sub_pipeline)
                continue
            sub_pipeline, act_kwargs = self.__init_builder(_("Redis集群扩缩容"), info)
            # 容量变更流程，分片数不变。这个地方不管前端传什么值，直接覆盖！！
            info["shard_num"] = act_kwargs.cluster["cluster_shard_num"]
            # 初始化计算一些常用参数
            ins_num = int(info["shard_num"] / info["group_num"])
            # 2024-05-30 实例允许有多有少。 这个地方利用取余计算出多余的redis实例数
            superfluous_ins_num = info["shard_num"] % info["group_num"]
            new_master_ips = []
            new_slave_ips = []
            new_ports = []
            for group_info in info["backend_group"]:
                new_master_ips.append(group_info["master"]["ip"])
                new_slave_ips.append(group_info["slave"]["ip"])
            for i in range(0, ins_num):
                new_ports.append(DEFAULT_REDIS_START_PORT + i)
            self.__pre_check(
                self.data["bk_biz_id"],
                info["cluster_id"],
                new_master_ips,
                new_slave_ips,
                info["shard_num"],
                info["group_num"],
            )
            # 安装实例
            redis_install_sub_pipelines = []
            params = {
                "meta_role": InstanceRole.REDIS_MASTER.value,
                "start_port": DEFAULT_REDIS_START_PORT,
                "spec_id": info["resource_spec"]["master"]["id"],
                "spec_config": info["resource_spec"]["master"],
            }
            # 靠前机器中，每个安装一个多余的实例
            cursor = superfluous_ins_num
            for ip in new_master_ips:
                params["ip"] = ip
                if cursor > 0:
                    cursor = cursor - 1
                    params["ports"] = new_ports + [DEFAULT_REDIS_START_PORT + ins_num]
                    params["instance_numb"] = ins_num + 1
                else:
                    params["ports"] = new_ports
                    params["instance_numb"] = ins_num
                redis_install_sub_pipelines.append(
                    RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
                )

            params = {
                "meta_role": InstanceRole.REDIS_SLAVE.value,
                "start_port": DEFAULT_REDIS_START_PORT,
                "spec_id": info["resource_spec"]["slave"]["id"],
                "spec_config": info["resource_spec"]["slave"],
            }
            cursor = superfluous_ins_num
            for ip in new_slave_ips:
                params["ip"] = ip
                if cursor > 0:
                    cursor = cursor - 1
                    params["ports"] = new_ports + [DEFAULT_REDIS_START_PORT + ins_num]
                    params["instance_numb"] = ins_num + 1
                else:
                    params["ports"] = new_ports
                    params["instance_numb"] = ins_num
                redis_install_sub_pipelines.append(
                    RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=redis_install_sub_pipelines)

            # 计算同步参数
            sync_relations = self.generate_sync_relation(
                act_kwargs=act_kwargs,
                master_ips=new_master_ips,
                slave_ips=new_slave_ips,
                ins_num=ins_num,
                superfluous_ins_num=superfluous_ins_num,
            )

            redis_sync_sub_pipelines = []
            for sync_params in sync_relations:
                if act_kwargs.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance:
                    pass
                sub_builder = RedisMakeSyncAtomJob(self.root_id, self.data, act_kwargs, sync_params)
                redis_sync_sub_pipelines.append(sub_builder)
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=redis_sync_sub_pipelines)

            # 如果是cluster架构切换后要把新slave给加入到集群，以及同步数据
            if is_redis_cluster_protocal(act_kwargs.cluster["cluster_type"]):
                sync_relations2 = self.generate_sync_relation(
                    act_kwargs=act_kwargs,
                    master_ips=new_slave_ips,
                    slave_ips=new_slave_ips,
                    ins_num=ins_num,
                    superfluous_ins_num=superfluous_ins_num,
                )

                redis_sync_sub_pipelines = []
                for sync_params in sync_relations2:
                    if act_kwargs.cluster["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance:
                        pass
                    sub_builder = RedisMakeSyncAtomJob(self.root_id, self.data, act_kwargs, sync_params)
                    redis_sync_sub_pipelines.append(sub_builder)
                sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=redis_sync_sub_pipelines)

            # 进行切换
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

            if is_redis_cluster_protocal(act_kwargs.cluster["cluster_type"]):
                # nodes写入元数据。这个必须在添加nodes域名之前
                # 这个地方的node需要先保证都是这种格式
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

                if access_sub_builder:
                    sub_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)
                # 如果这里为空，说明之前并不存在nodes接入层记录，此时，需要用另一种方式初始化nodes域名
                else:
                    dns_kwargs = DnsKwargs(
                        dns_op_type=DnsOpType.CREATE,
                        add_domain_name="nodes." + act_kwargs.cluster["immute_domain"],
                        dns_op_exec_port=DEFAULT_REDIS_START_PORT,
                    )

                    act_kwargs.exec_ip = new_master_ips + new_slave_ips
                    sub_pipeline.add_act(
                        act_name=_("初始化新增nodes域名"),
                        act_component_code=RedisDnsManageComponent.code,
                        kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
                    )

            sub_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})

            if is_redis_cluster_protocal(act_kwargs.cluster["cluster_type"]):
                # 删除老实例的nodes域名
                params = {
                    "cluster_id": info["cluster_id"],
                    "port": DEFAULT_REDIS_START_PORT,
                    "del_ips": act_kwargs.cluster["old_master_list"] + act_kwargs.cluster["old_slave_list"],
                    "op_type": DnsOpType.RECYCLE_RECORD,
                    "role": [ClusterEntryRole.NODE_ENTRY.value],
                }
                access_sub_builder = AccessManagerAtomJob(self.root_id, self.data, act_kwargs, params)
                if access_sub_builder:
                    sub_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)

            # 下架老实例
            redis_shutdown_sub_pipelines = []
            act_kwargs.cluster["created_by"] = self.data["created_by"]
            shutdown_ip_ports = self.generate_shutdown_ins(act_kwargs)
            shutdown_ignore_ips = self.generate_shutdown_ignore_ips(act_kwargs)
            for ip, ports in shutdown_ip_ports.items():
                params = {"ip": ip, "ports": ports, "ignore_ips": shutdown_ignore_ips[ip], "force_shutdown": False}
                redis_shutdown_sub_pipelines.append(
                    RedisBatchShutdownAtomJob(self.root_id, self.data, act_kwargs, params)
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=redis_shutdown_sub_pipelines)

            # 更新 dbconfig 中版本信息
            act_kwargs.cluster["cluster_domain"] = act_kwargs.cluster["immute_domain"]
            act_kwargs.cluster["current_version"] = act_kwargs.cluster["origin_db_version"]
            act_kwargs.cluster["target_version"] = act_kwargs.cluster["db_version"]
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_dbconfig.__name__
            sub_pipeline.add_act(
                act_name=_("Redis-更新dbconfig中集群版本"),
                act_component_code=RedisConfigComponent.code,
                kwargs=asdict(act_kwargs),
            )

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
                sub_pipeline.build_sub_process(sub_name=_("{}backend扩缩容").format(act_kwargs.cluster["immute_domain"]))
            )

        redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)
        redis_pipeline.run_pipeline()
