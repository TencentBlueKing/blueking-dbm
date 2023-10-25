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
import copy
import json
import logging.config
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.flow.consts import DEFAULT_REDIS_START_PORT, DEFAULT_TWEMPROXY_SEG_TOTOL_NUM, ClusterStatus, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ProxyBatchInstallAtomJob, RedisBatchInstallAtomJob
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode
from backend.flow.utils.redis.redis_util import check_domain

logger = logging.getLogger("flow")


class RedisClusterApplyFlow(object):
    """
    构建redis集群申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

        # 兼容手工部署,填充fake的规格信息，将master/slave进行分组。TODO：去掉手动部署后需要废弃
        if "resource_spec" not in self.data:
            self.data["resource_spec"] = {
                "master": {"id": 0},
                "slave": {"id": 0},
                "proxy": {"id": 0},
            }
            self.data["nodes"]["backend_group"] = []
            for index in range(len(self.data["nodes"]["master"])):
                master, slave = self.data["nodes"]["master"][index], self.data["nodes"]["slave"][index]
                self.data["nodes"]["backend_group"].append({"master": master, "slave": slave})

            self.data["nodes"].pop("master")
            self.data["nodes"].pop("slave")

    def __pre_check(self, proxy_ips, master_ips, slave_ips, group_num, shard_num, servers, domain):
        """
        前置检查，检查传参
        """
        ips = proxy_ips + master_ips + slave_ips
        if len(set(ips)) != len(ips):
            raise Exception("have ip address has been used multiple times.")
        if len(master_ips) != len(slave_ips):
            raise Exception("master machine len != slave machine len.")
        if len(master_ips) != group_num:
            raise Exception("machine len != group_num.")
        if len(servers) != shard_num:
            raise Exception("servers len ({}) != shard_num ({}).".format(len(servers), shard_num))
        if shard_num % group_num != 0:
            raise Exception("shard_num ({}) % group_num ({}) != 0.".format(shard_num, group_num))
        if not check_domain(domain):
            raise Exception("domain[{}] is illegality.".format(domain))
        d = Cluster.objects.filter(immute_domain=domain).values("immute_domain")
        if len(d) != 0:
            raise Exception("domain [{}] is used.".format(domain))
        m = Machine.objects.filter(ip__in=ips).values("ip")
        if len(m) != 0:
            raise Exception("[{}] is used.".format(m))

    def cal_twemproxy_serveres(self, master_ips, slave_ips, shard_num, inst_num, name):
        """
        计算twemproxy的servers 列表
        - redisip:redisport:1 app beginSeg-endSeg 1
        "servers": ["x.x.x.x:30000  xxx 0-219999 1","x.x.x.x:30001  xxx 220000-419999 1"]
        """
        seg_num = DEFAULT_TWEMPROXY_SEG_TOTOL_NUM // shard_num
        seg_no = 0

        #  计算分片
        servers = []
        twemproxy_server_shards = defaultdict(dict)
        for _index, master_ip in enumerate(master_ips):
            slave_ip = slave_ips[_index]
            for inst_no in range(0, inst_num):
                port = DEFAULT_REDIS_START_PORT + inst_no
                begin_seg = seg_no * seg_num
                end_seg = seg_num * (seg_no + 1) - 1
                if _index == len(master_ips) - 1:
                    if inst_no == inst_num - 1 and end_seg != DEFAULT_TWEMPROXY_SEG_TOTOL_NUM:
                        end_seg = DEFAULT_TWEMPROXY_SEG_TOTOL_NUM - 1
                if begin_seg >= DEFAULT_TWEMPROXY_SEG_TOTOL_NUM or end_seg >= DEFAULT_TWEMPROXY_SEG_TOTOL_NUM:
                    raise Exception("cal_twemproxy_serveres error. pleace check params")
                seg_no = seg_no + 1
                servers.append("{}:{} {} {}-{} {}".format(master_ip, port, name, begin_seg, end_seg, 1))
                master_inst = "{}:{}".format(master_ip, port)
                slave_inst = "{}:{}".format(slave_ip, port)
                twemproxy_server_shards[master_ip][master_inst] = "{}-{}".format(begin_seg, end_seg)
                twemproxy_server_shards[slave_ip][slave_inst] = "{}-{}".format(begin_seg, end_seg)
        return servers, twemproxy_server_shards

    def deploy_redis_cluster_flow(self):
        """
        部署Redis集群
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        proxy_ips = [info["ip"] for info in self.data["nodes"]["proxy"]]
        master_ips = [info["master"]["ip"] for info in self.data["nodes"]["backend_group"]]
        slave_ips = [info["slave"]["ip"] for info in self.data["nodes"]["backend_group"]]

        ins_num = self.data["shard_num"] // self.data["group_num"]
        ports = list(map(lambda i: i + DEFAULT_REDIS_START_PORT, range(ins_num)))
        servers, twemproxy_server_shards = self.cal_twemproxy_serveres(
            master_ips, slave_ips, self.data["shard_num"], ins_num, self.data["cluster_name"]
        )

        self.__pre_check(
            proxy_ips,
            master_ips,
            slave_ips,
            self.data["group_num"],
            self.data["shard_num"],
            servers,
            self.data["domain_name"],
        )
        cluster_tpl = {
            "immute_domain": self.data["domain_name"],
            "cluster_type": self.data["cluster_type"],
            "db_version": self.data["db_version"],
            "bk_biz_id": self.data["bk_biz_id"],
            "bk_cloud_id": self.data["bk_cloud_id"],
            "created_by": self.data["created_by"],
            "cluster_name": self.data["cluster_name"],
        }

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 安装redis子流程
        params = {
            "instance_numb": ins_num,
            "ports": ports,
            "start_port": DEFAULT_REDIS_START_PORT,
            "requirepass": self.data["redis_pwd"],
            "databases": self.data["databases"],
            "maxmemory": self.data["maxmemory"],
        }
        sub_pipelines = []
        for ip in master_ips:
            act_kwargs.cluster = copy.deepcopy(cluster_tpl)

            params["ip"] = ip
            params["spec_id"] = int(self.data["resource_spec"]["master"]["id"])
            params["spec_config"] = self.data["resource_spec"]["master"]
            params["meta_role"] = InstanceRole.REDIS_MASTER.value
            params["server_shards"] = twemproxy_server_shards[ip]
            params["cache_backup_mode"] = get_cache_backup_mode(self.data["bk_biz_id"], 0)
            sub_builder = RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        for ip in slave_ips:
            # 为了解决重复问题，cluster重新赋值一下
            act_kwargs.cluster = copy.deepcopy(cluster_tpl)

            params["ip"] = ip
            params["spec_id"] = int(self.data["resource_spec"]["slave"]["id"])
            params["spec_config"] = self.data["resource_spec"]["slave"]
            params["meta_role"] = InstanceRole.REDIS_SLAVE.value
            params["server_shards"] = twemproxy_server_shards[ip]
            params["cache_backup_mode"] = get_cache_backup_mode(self.data["bk_biz_id"], 0)
            sub_builder = RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 建立主从关系。 新建集群时的主从关系直接salveof就行
        bacth_pairs = []
        act_kwargs.cluster = copy.deepcopy(cluster_tpl)
        common = {
            "master_start_port": DEFAULT_REDIS_START_PORT,
            "master_inst_num": ins_num,
            "master_auth": self.data["redis_pwd"],
            "slave_start_port": DEFAULT_REDIS_START_PORT,
            "slave_inst_num": ins_num,
            "slave_password": self.data["redis_pwd"],
        }
        for _index, master_ip in enumerate(master_ips):
            slave_ip = slave_ips[_index]
            bp = copy.deepcopy(common)
            bp["master_ip"] = master_ip
            bp["slave_ip"] = slave_ip
            bacth_pairs.append(bp)
        act_kwargs.cluster["bacth_pairs"] = bacth_pairs
        act_kwargs.exec_ip = master_ips[0]
        act_kwargs.get_redis_payload_func = RedisActPayload.get_slaveof_redis_payload.__name__
        redis_pipeline.add_act(
            act_name=_("建立主从关系"), act_component_code=ExecuteDBActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.cluster = {
            "bacth_pairs": bacth_pairs,
            "created_by": self.data["created_by"],
            "start_port": DEFAULT_REDIS_START_PORT,
            "inst_num": ins_num,
            "meta_func_name": RedisDBMeta.replicaof.__name__,
        }
        redis_pipeline.add_act(
            act_name=_("redis建立主从 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 安装proxy子流程
        sub_pipelines = []
        params = {
            "spec_id": int(self.data["resource_spec"]["proxy"]["id"]),
            "spec_config": self.data["resource_spec"]["proxy"],
            "redis_pwd": self.data["redis_pwd"],
            "proxy_pwd": self.data["proxy_pwd"],
            "proxy_port": self.data["proxy_port"],
            "servers": servers,
        }
        for ip in proxy_ips:
            act_kwargs.cluster = copy.deepcopy(cluster_tpl)

            params["ip"] = ip
            sub_builder = ProxyBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 建立集群关系
        act_kwargs.cluster = {
            "new_proxy_ips": proxy_ips,
            "servers": servers,
            "proxy_port": self.data["proxy_port"],
            "cluster_type": self.data["cluster_type"],
            "bk_biz_id": self.data["bk_biz_id"],
            "bk_cloud_id": self.data["bk_cloud_id"],
            "cluster_name": self.data["cluster_name"],
            "cluster_alias": self.data["cluster_alias"],
            "db_version": self.data["db_version"],
            "immute_domain": self.data["domain_name"],
            "created_by": self.data["created_by"],
            "region": self.data.get("city_code", ""),
            "meta_func_name": RedisDBMeta.redis_make_cluster.__name__,
        }
        redis_pipeline.add_act(
            act_name=_("建立集群 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        acts_list = []
        act_kwargs.cluster = {
            "conf": {
                "maxmemory": str(self.data["maxmemory"]),
                "databases": str(self.data["databases"]),
                "requirepass": self.data["redis_pwd"],
            },
            "db_version": self.data["db_version"],
            "domain_name": self.data["domain_name"],
        }
        if self.data["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
            act_kwargs.cluster["conf"]["cluster-enabled"] = ClusterStatus.REDIS_CLUSTER_NO

        act_kwargs.get_redis_payload_func = RedisActPayload.set_redis_config.__name__
        acts_list.append(
            {
                "act_name": _("回写集群配置[Redis]"),
                "act_component_code": RedisConfigComponent.code,
                "kwargs": asdict(act_kwargs),
            },
        )

        act_kwargs.cluster = {
            "conf": {
                "password": self.data["proxy_pwd"],
                "redis_password": self.data["redis_pwd"],
                "port": str(self.data["proxy_port"]),
            },
            "domain_name": self.data["domain_name"],
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.set_proxy_config.__name__
        acts_list.append(
            {
                "act_name": _("回写集群配置[Twemproxy]"),
                "act_component_code": RedisConfigComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )

        # 添加域名
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.CREATE,
            add_domain_name=self.data["domain_name"],
            dns_op_exec_port=self.data["proxy_port"],
        )
        act_kwargs.exec_ip = proxy_ips
        acts_list.append(
            {
                "act_name": _("注册域名"),
                "act_component_code": RedisDnsManageComponent.code,
                "kwargs": {**asdict(act_kwargs), **asdict(dns_kwargs)},
            }
        )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        redis_pipeline.run_pipeline()
