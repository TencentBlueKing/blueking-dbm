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
from typing import Any, Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta import api
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigFileEnum, ConfigTypeEnum, DnsOpType, SyncType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    ProxyBatchInstallAtomJob,
    ProxyUnInstallAtomJob,
    RedisClusterMasterReplaceJob,
    RedisClusterSlaveReplaceJob,
)
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

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
            "redis_proxy": [
                {
                    "old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
                    "new": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123}
                }],
            "redis_slave": [
                {
                    "old": {"ip": "2.b.3.4", "bk_cloud_id": 0, "bk_host_id": 123},
                    "new": {"ip": "2.b.3.4", "bk_cloud_id": 0, "bk_host_id": 123}
                }],
            "redis_master": [
                {
                    "old": {"ip": "2.2.3.c", "bk_cloud_id": 0, "bk_host_id": 123},
                    "new": [{"ip": "2.2.3.c", "bk_cloud_id": 0, "bk_host_id": 123},]
                }]
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
        self.precheck_for_compelete_replace()

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

            cluster_info = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)[0]
            cluster_name = cluster_info["name"]
            cluster_type = cluster_info["cluster_type"]
            redis_master_set = cluster_info["redis_master_set"]
            redis_slave_set = cluster_info["redis_slave_set"]
            servers = []
            if cluster_type in [ClusterType.TendisTwemproxyRedisInstance, ClusterType.TwemproxyTendisSSDInstance]:
                for set in redis_master_set:
                    ip_port, seg_range = str.split(set)
                    servers.append("{} {} {} {}".format(ip_port, cluster_name, seg_range, 1))
            else:
                servers = redis_master_set + redis_slave_set

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
            "backend_servers": servers,
        }

    @staticmethod
    def __get_cluster_config(bk_biz_id: int, namespace: str, domain_name: str, db_version: str) -> Any:
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": domain_name,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": db_version,
                "conf_type": ConfigTypeEnum.ProxyConf.value,
                "namespace": namespace,
                "format": FormatType.MAP.value,
            }
        )
        return data["content"]

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

    # 这里整理替换所需要的参数
    def complete_machine_replace(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS-整机替换"))
        sub_pipelines = []
        for cluster_replacement in self.data["infos"]:

            cluster_kwargs = deepcopy(act_kwargs)
            cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], cluster_replacement["cluster_id"])
            sync_type = SyncType.SYNC_MMS.value  # ssd sync from master
            if cluster_info["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
                sync_type = SyncType.SYNC_SMS.value

            flow_data = self.data
            for k, v in cluster_info.items():
                cluster_kwargs.cluster[k] = v
            cluster_kwargs.cluster["created_by"] = self.data["created_by"]
            flow_data["sync_type"] = sync_type
            flow_data["replace_info"] = cluster_replacement
            redis_pipeline.add_act(
                act_name=_("初始化配置-{}".format(cluster_info["immute_domain"])),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(cluster_kwargs),
            )
            sub_pipeline = self.generate_cluster_replacement(flow_data, cluster_kwargs, cluster_replacement)
            sub_pipelines.append(sub_pipeline)

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        return redis_pipeline.run_pipeline()

    # 组装&控制 集群替换流程
    def generate_cluster_replacement(self, flow_data, act_kwargs, replacement_param):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)

        # 先添加Slave替换流程
        if replacement_param.get("redis_slave"):
            slave_kwargs = deepcopy(act_kwargs)
            slave_replace_pipe = RedisClusterSlaveReplaceJob(
                self.root_id, flow_data, slave_kwargs, replacement_param.get("redis_slave")
            )
            sub_pipeline.add_sub_pipeline(slave_replace_pipe)

        # 再添加Proxy替换流程
        if replacement_param.get("redis_proxy"):
            proxy_kwargs = deepcopy(act_kwargs)
            self.proxy_replacement(sub_pipeline, proxy_kwargs, replacement_param.get("redis_proxy"))

        # 最后添加Master替换流程 , reget proxy info.
        if replacement_param.get("redis_master"):
            master_kwargs = deepcopy(act_kwargs)
            cluster = Cluster.objects.get(
                id=master_kwargs.cluster["cluster_id"], bk_biz_id=master_kwargs.cluster["bk_biz_id"]
            )
            master_kwargs.cluster["proxy_ips"] = [
                proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()
            ]
            master_kwargs.cluster["sync_type"] = flow_data["sync_type"]
            master_replace_pipe = RedisClusterMasterReplaceJob(
                self.root_id, flow_data, master_kwargs, replacement_param.get("redis_master")
            )
            sub_pipeline.add_sub_pipeline(master_replace_pipe)

        return sub_pipeline.build_sub_process(sub_name=_("Redis-{}-整机替换").format(act_kwargs.cluster["immute_domain"]))

    def proxy_replacement(self, sub_pipeline, act_kwargs, proxy_replace_details):
        old_proxies, new_proxies = [], []
        for replace_link in proxy_replace_details:
            # "Old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
            old_proxies.append(replace_link["old"]["ip"])
            new_proxies.append(replace_link["new"]["ip"])

        # 第一步：安装Proxy
        sub_pipelines = []
        if act_kwargs.cluster["cluster_type"] in [
            ClusterType.TendisTwemproxyRedisInstance.value,
            ClusterType.TwemproxyTendisSSDInstance.value,
        ]:
            proxy_version = ConfigFileEnum.Twemproxy
        else:
            proxy_version = ConfigFileEnum.Predixy

        config_info = self.__get_cluster_config(
            self.data["bk_biz_id"],
            act_kwargs.cluster["cluster_type"],
            act_kwargs.cluster["immute_domain"],
            proxy_version,
        )

        for proxy_ip in new_proxies:
            params = {
                "ip": proxy_ip,
                "redis_pwd": config_info["redis_password"],
                "proxy_pwd": config_info["password"],
                "proxy_port": int(config_info["port"]),
                "servers": act_kwargs.cluster["backend_servers"],
            }
            sub_builder = ProxyBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        act_kwargs.cluster["proxy_ips"] = new_proxies
        act_kwargs.cluster["proxy_port"] = int(config_info["port"])
        act_kwargs.cluster["meta_func_name"] = RedisDBMeta.proxy_add_cluster.__name__
        act_kwargs.cluster["domain_name"] = act_kwargs.cluster["immute_domain"]
        sub_pipeline.add_act(
            act_name=_("Proxy-加入集群-{}".format(act_kwargs.cluster["immute_domain"])),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 第二步：接入层管理：填加新接入层
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.CREATE.value,
            add_domain_name=act_kwargs.cluster["immute_domain"],
            dns_op_exec_port=int(config_info["port"]),
        )
        act_kwargs.exec_ip = new_proxies
        sub_pipeline.add_act(
            act_name=_("Proxy-注册域名-{}".format(act_kwargs.cluster["immute_domain"])),
            act_component_code=RedisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )
        # 第三步：接入层管理：清理旧接入层(这里可能需要留点时间然后在执行下一步)
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.RECYCLE_RECORD,
            add_domain_name=act_kwargs.cluster["immute_domain"],
            dns_op_exec_port=int(config_info["port"]),
        )
        act_kwargs.exec_ip = old_proxies
        sub_pipeline.add_act(
            act_name=_("Proxy-回收域名-{}".format(act_kwargs.cluster["immute_domain"])),
            act_component_code=RedisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )
        # 第四步：卸载Proxy
        proxy_down_pipelines = []
        for proxy_ip in old_proxies:
            params = {"ip": proxy_ip, "proxy_port": act_kwargs.cluster["proxy_port"]}
            sub_builder = ProxyUnInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            proxy_down_pipelines.append(sub_builder)
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=proxy_down_pipelines)

    # 存在性检查
    def precheck_for_compelete_replace(self):
        for cluster_replacement in self.data["infos"]:
            try:
                cluster = Cluster.objects.get(id=cluster_replacement["cluster_id"], bk_biz_id=self.data["bk_biz_id"])
            except Cluster.DoesNotExist as e:
                raise Exception("redis cluster does not exist,{}", e)
            # check proxy
            for proxy in cluster_replacement.get("redis_proxy", []):
                if not cluster.proxyinstance_set.filter(machine__ip=proxy["old"]["ip"]):
                    raise Exception("proxy {} does not exist in cluster {}", proxy["old"]["ip"], cluster.immute_domain)
            # check slave
            for slave in cluster_replacement.get("redis_slave", []):
                if not cluster.storageinstance_set.filter(
                    machine__ip=slave["old"]["ip"], instance_role=InstanceRole.REDIS_SLAVE.value
                ):
                    raise Exception("slave {} does not exist in cluster {}", slave["old"]["ip"], cluster.immute_domain)
            # check master
            for master in cluster_replacement.get("redis_master", []):
                if not cluster.storageinstance_set.filter(
                    machine__ip=master["old"]["ip"], instance_role=InstanceRole.REDIS_MASTER.value
                ):
                    raise Exception(
                        "master {} does not exist in cluster {}", master["old"]["ip"], cluster.immute_domain
                    )
