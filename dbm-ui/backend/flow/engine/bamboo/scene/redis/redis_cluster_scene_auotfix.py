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
import logging.config
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta import api
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import (
    DEFAULT_DB_MODULE_ID,
    DEFAULT_REDIS_START_PORT,
    ConfigFileEnum,
    ConfigTypeEnum,
    DnsOpType,
    SyncType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    AccessManagerAtomJob,
    ProxyBatchInstallAtomJob,
    RedisBatchInstallAtomJob,
    RedisMakeSyncAtomJob,
    StorageRepLink,
)
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellReloadMetaComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_ticket import RedisTicketComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_cache_backup_mode, get_twemproxy_cluster_server_shards
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class RedisClusterAutoFixSceneFlow(object):
    """
    tendis fault autofix 4 host
    这里只做新增,以及管理层的清理操作,真正下发 actor 下架实例的操作单独提单据
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"vitox",
        "ticket_type":"REDIS_CLUSTER_AUTOFIX",
        "infos": [
            {
            "cluster_id": 1,
            "proxy": [
                   {"ip": "1.1.1.a","spec_id": 17,
                  "target": {"bk_cloud_id": 0,"bk_host_id": 216,"status": 1,"ip": "2.2.2.b"}
                  }],
            "redis_slave": [
                 {"ip": "1.1.1.a","spec_id": 17,
                  "target": {"bk_cloud_id": 0,"bk_host_id": 216,"status": 1,"ip": "2.2.2.b"}
                 }],
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
        self.precheck_for_instance_fix()

    @staticmethod
    def get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群现有信息
        1. master 对应 slave 机器
        2. master 上的端口列表
        3. 实例对应关系：{master:port:slave:port}
        """
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        master_ports, slave_ports = defaultdict(list), defaultdict(list)
        slave_master_map, slave_ins_map = defaultdict(), defaultdict()

        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            master_ports[master_obj.machine.ip].append(master_obj.port)
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

        cluster_info = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)[0]
        redis_master_set, redis_slave_set, servers = (
            cluster_info["redis_master_set"],
            cluster_info["redis_slave_set"],
            [],
        )
        if cluster.cluster_type in [ClusterType.TendisTwemproxyRedisInstance, ClusterType.TwemproxyTendisSSDInstance]:
            for set in redis_master_set:
                ip_port, seg_range = str.split(set)
                servers.append("{} {} {} {}".format(ip_port, cluster.name, seg_range, 1))
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
            "slave_ins_map": dict(slave_ins_map),
            "slave_master_map": dict(slave_master_map),
            "proxy_port": cluster.proxyinstance_set.first().port,
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "db_version": cluster.major_version,
            "backend_servers": servers,
        }

    @staticmethod
    def __get_cluster_config(bk_biz_id: int, namespace: str, domain_name: str, db_version: str) -> Any:
        """
        获取已部署的实例配置
        """
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

        passwd_ret = PayloadHandler.redis_get_password_by_domain(domain_name)
        if passwd_ret.get("redis_password"):
            data["content"]["redis_password"] = passwd_ret.get("redis_password")
        if passwd_ret.get("redis_proxy_password"):
            data["content"]["password"] = passwd_ret.get("redis_proxy_password")
        if passwd_ret.get("redis_proxy_admin_password"):
            data["content"]["redis_proxy_admin_password"] = passwd_ret.get("redis_proxy_admin_password")

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
    def start_redis_auotfix(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS-故障自愈"))
        sub_pipelines = []
        for cluster_fix in self.data["infos"]:
            cluster_kwargs = deepcopy(act_kwargs)
            cluster_info = self.get_cluster_info(self.data["bk_biz_id"], cluster_fix["cluster_id"])
            flow_data = self.data
            for k, v in cluster_info.items():
                cluster_kwargs.cluster[k] = v
            cluster_kwargs.cluster["created_by"] = self.data["created_by"]
            flow_data["fix_info"] = cluster_fix
            redis_pipeline.add_act(
                act_name=_("初始化配置-{}".format(cluster_info["immute_domain"])),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(cluster_kwargs),
            )
            sub_pipelines.append(self.cluster_fix(flow_data, cluster_kwargs, cluster_fix))

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        return redis_pipeline.run_pipeline()

    # 组装&控制 集群替换流程
    def cluster_fix(self, flow_data, act_kwargs, fix_params):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)

        # 先补充slave
        if fix_params.get("redis_slave"):
            slave_kwargs = deepcopy(act_kwargs)
            sub_pipeline.add_sub_pipeline(
                self.slave_fix(
                    flow_data,
                    slave_kwargs,
                    {
                        "redis_slave": fix_params.get("redis_slave"),
                        "slave_spec": fix_params.get("resource_spec", {}).get("redis_slave", {}),
                    },
                )
            )

        # 然后在搞定proxy
        if fix_params.get("proxy"):
            proxy_kwargs = deepcopy(act_kwargs)
            sub_pipeline.add_sub_pipeline(
                self.proxy_fix(
                    flow_data,
                    proxy_kwargs,
                    {
                        "proxy": fix_params.get("proxy"),
                        "proxy_spec": fix_params.get("resource_spec", {}).get("proxy", {}),
                    },
                )
            )

        return sub_pipeline.build_sub_process(sub_name=_("故障自愈-{}").format(act_kwargs.cluster["immute_domain"]))

    def proxy_fix(self, flow_data, act_kwargs, proxy_fix_info):
        old_proxies, new_proxies, proxy_fix_details = [], [], proxy_fix_info["proxy"]
        sub_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)

        for fix_link in proxy_fix_details:
            old_proxies.append(fix_link["ip"])
            new_proxies.append(fix_link["target"]["ip"])

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
            replace_kwargs = copy.deepcopy(act_kwargs)
            params = {
                "ip": proxy_ip,
                "redis_pwd": config_info["redis_password"],
                "proxy_pwd": config_info["password"],
                "proxy_admin_pwd": config_info["redis_proxy_admin_password"],
                "conf_configs": config_info,
                "proxy_port": int(config_info["port"]),
                "servers": replace_kwargs.cluster["backend_servers"],
                "spec_id": proxy_fix_info["proxy_spec"].get("id", 0),
                "spec_config": proxy_fix_info["proxy_spec"],
            }
            sub_pipelines.append(ProxyBatchInstallAtomJob(self.root_id, self.data, replace_kwargs, params))
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 第二步：元数据加入集群
        act_kwargs.cluster["proxy_ips"] = new_proxies
        act_kwargs.cluster["proxy_port"] = int(config_info["port"])
        act_kwargs.cluster["meta_func_name"] = RedisDBMeta.proxy_add_cluster.__name__
        act_kwargs.cluster["domain_name"] = act_kwargs.cluster["immute_domain"]
        sub_pipeline.add_act(
            act_name=_("Proxy-加入集群-{}".format(new_proxies)),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 第三步: 新-接入层注册
        sub_pipeline.add_sub_pipeline(
            sub_flow=AccessManagerAtomJob(
                self.root_id,
                self.data,
                act_kwargs,
                {
                    "cluster_id": act_kwargs.cluster["cluster_id"],
                    "port": act_kwargs.cluster["proxy_port"],
                    "add_ips": new_proxies,
                    "op_type": DnsOpType.CREATE.value,
                },
            )
        )

        # 第四步: 旧-接入层剔除, 理论上这里DBHA已经清理过了
        sub_pipeline.add_sub_pipeline(
            sub_flow=AccessManagerAtomJob(
                self.root_id,
                self.data,
                act_kwargs,
                {
                    "cluster_id": act_kwargs.cluster["cluster_id"],
                    "port": act_kwargs.cluster["proxy_port"],
                    "del_ips": old_proxies,
                    "op_type": DnsOpType.RECYCLE_RECORD.value,
                },
            )
        )

        # # 第五步：卸载Proxy （生产Ticket单据）
        sub_pipeline.add_act(
            act_name=_("提交Proxy下架单-{}".format(old_proxies)),
            act_component_code=RedisTicketComponent.code,
            kwargs={
                "bk_biz_id": act_kwargs.cluster["bk_biz_id"],
                "cluster_id": act_kwargs.cluster["cluster_id"],
                "immute_domain": act_kwargs.cluster["immute_domain"],
                "ticket_type": TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value,
                "ticket_details": {
                    "cluster_id": act_kwargs.cluster["cluster_id"],
                    "proxy": old_proxies,
                },
            },
        )

        return sub_pipeline.build_sub_process(sub_name=_("Proxy自愈-{}").format(act_kwargs.cluster["immute_domain"]))

    def slave_fix(self, flow_data, sub_kwargs, slave_fix_info):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)
        slave_fix_detail = slave_fix_info["redis_slave"]
        newslave_to_master, replace_link_info = {}, {}

        for fix_link in slave_fix_detail:
            old_slave, new_slave = fix_link["ip"], fix_link["target"]["ip"]
            new_ins_port = DEFAULT_REDIS_START_PORT
            old_ports = sub_kwargs.cluster["slave_ports"][old_slave]
            old_ports.sort()  # 升序
            for port in old_ports:
                one_link = StorageRepLink()
                one_link.old_slave_ip, one_link.old_slave_port = old_slave, int(port)
                one_link.new_slave_ip, one_link.new_slave_port = new_slave, new_ins_port

                old_slave_addr = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, port)
                new_slave_addr = "{}{}{}".format(new_slave, IP_PORT_DIVIDER, new_ins_port)
                old_master_addr = sub_kwargs.cluster["slave_ins_map"].get(
                    old_slave_addr, "none.old.ip.{}:0".format(old_slave_addr)
                )

                one_link.old_master_ip = old_master_addr.split(IP_PORT_DIVIDER)[0]
                one_link.old_master_port = int(old_master_addr.split(IP_PORT_DIVIDER)[1])

                newslave_to_master[new_slave_addr] = old_master_addr
                replace_link_info[old_slave_addr] = one_link
                new_ins_port += 1

        twemproxy_server_shards = get_twemproxy_cluster_server_shards(
            sub_kwargs.cluster["bk_biz_id"], sub_kwargs.cluster["cluster_id"], newslave_to_master
        )
        # ### 部署实例 ###############################################################################
        sub_pipelines = []
        for fix_link in slave_fix_detail:
            old_slave = fix_link["ip"]
            new_slave = fix_link["target"]["ip"]
            params = {
                "ip": new_slave,
                "meta_role": InstanceRole.REDIS_SLAVE.value,
                "start_port": DEFAULT_REDIS_START_PORT,
                "ports": sub_kwargs.cluster["slave_ports"][old_slave],
                "instance_numb": len(sub_kwargs.cluster["slave_ports"][old_slave]),
                "spec_id": slave_fix_info["slave_spec"].get("id", 0),
                "spec_config": slave_fix_info["slave_spec"],
                "server_shards": twemproxy_server_shards.get(new_slave, {}),
                "cache_backup_mode": get_cache_backup_mode(
                    sub_kwargs.cluster["bk_biz_id"], sub_kwargs.cluster["cluster_id"]
                ),
            }
            sub_builder = RedisBatchInstallAtomJob(self.root_id, flow_data, sub_kwargs, params)
            sub_pipelines.append(sub_builder)
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # ### 部署实例 ######################################################################## 完毕 ###

        # #### 建同步关系 ##############################################################################
        sub_pipelines = []
        for fix_link in slave_fix_detail:
            # "Old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
            old_slave = fix_link["ip"]
            new_slave = fix_link["target"]["ip"]
            install_params = {
                "sync_type": SyncType.SYNC_MS,
                "origin_1": sub_kwargs.cluster["slave_master_map"][old_slave],
                "origin_2": old_slave,
                "sync_dst1": new_slave,
                "ins_link": [],
                "server_shards": twemproxy_server_shards.get(new_slave, {}),
                "cache_backup_mode": get_cache_backup_mode(
                    sub_kwargs.cluster["bk_biz_id"], sub_kwargs.cluster["cluster_id"]
                ),
            }
            for slave_port in sub_kwargs.cluster["slave_ports"][old_slave]:
                old_ins = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, slave_port)
                rep_link = replace_link_info.get(old_ins, StorageRepLink())
                install_params["ins_link"].append(
                    {
                        "origin_1": rep_link.old_master_port,
                        "origin_2": rep_link.old_slave_port,
                        "sync_dst1": rep_link.new_slave_port,
                    }
                )
            sub_builder = RedisMakeSyncAtomJob(self.root_id, flow_data, sub_kwargs, install_params)
            sub_pipelines.append(sub_builder)
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # #### 建同步关系 ##################################################################### 完毕 ####

        # 新节点加入集群 ################################################################################
        sub_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_redo_slaves.__name__
        sub_kwargs.cluster["old_slaves"] = []
        sub_kwargs.cluster["created_by"] = flow_data["created_by"]
        sub_kwargs.cluster["tendiss"] = []
        for fix_link in slave_fix_detail:
            old_slave, new_slave = fix_link["ip"], fix_link["target"]["ip"]
            sub_kwargs.cluster["old_slaves"].append(
                {"ip": old_slave, "ports": sub_kwargs.cluster["slave_ports"][old_slave]}
            )
            for slave_port in sub_kwargs.cluster["slave_ports"][old_slave]:
                old_ins = "{}{}{}".format(old_slave, IP_PORT_DIVIDER, slave_port)
                rep_link = replace_link_info.get(old_ins, StorageRepLink())
                sub_kwargs.cluster["tendiss"].append(
                    {
                        "ejector": {
                            "ip": rep_link.old_master_ip,
                            "port": rep_link.old_master_port,
                        },
                        "receiver": {"ip": rep_link.new_slave_ip, "port": int(rep_link.new_slave_port)},
                    }
                )
        sub_pipeline.add_act(
            act_name=_("Redis-新节点加入集群"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(sub_kwargs)
        )
        # #### 新节点加入集群 ################################################################# 完毕 ###

        # predixy类型的集群需要刷新配置文件 #################################################################
        if sub_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value:
            sed_args = []
            for fix_link in slave_fix_detail:
                old_slave, new_slave = fix_link["ip"], fix_link["target"]["ip"]
                for slave_port in sub_kwargs.cluster["slave_ports"][old_slave]:
                    sed_args.append(
                        "-e 's/{}{}{}/{}{}{}/'".format(
                            old_slave, IP_PORT_DIVIDER, slave_port, new_slave, IP_PORT_DIVIDER, slave_port
                        )
                    )
            sed_seed = " ".join(sed_args)
            sub_kwargs.cluster[
                "shell_command"
            ] = """
            cnf="$REDIS_DATA_DIR/predixy/{}/predixy.conf"
            echo "`date "+%F %T"` : before sed config $cnf: : `cat $cnf |grep  "+"|grep ":"`"
            echo "`date "+%F %T"` : exec sed -i {}"
            sed -i {} $cnf
            echo "`date "+%F %T"` : after sed configs : `cat $cnf |grep "+"|grep ":"`"
            """.format(
                sub_kwargs.cluster["proxy_port"], sed_seed, sed_seed
            )

            sub_pipeline.add_act(
                act_name=_("刷新Predixy本地配置"),
                act_component_code=ExecuteShellReloadMetaComponent.code,
                kwargs=asdict(sub_kwargs),
            )
        # predixy类型的集群需要刷新配置文件 ######################################################## 完毕 ###

        # # #### 下架旧实例 （生产Ticket单据） ################################################## 完毕 ###
        old_slaves = [fix_link["ip"] for fix_link in slave_fix_detail]
        sub_pipeline.add_act(
            act_name=_("提交Redis下架单-{}".format(old_slaves)),
            act_component_code=RedisTicketComponent.code,
            kwargs={
                "bk_biz_id": sub_kwargs.cluster["bk_biz_id"],
                "cluster_id": sub_kwargs.cluster["cluster_id"],
                "immute_domain": sub_kwargs.cluster["immute_domain"],
                "ticket_type": TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value,
                "ticket_details": {
                    "cluster_id": sub_kwargs.cluster["cluster_id"],
                    "redis_slave": old_slaves,
                },
            },
        )
        # # #### 下架旧实例 ###################################################################### 完毕 ###

        return sub_pipeline.build_sub_process(sub_name=_("Slave替换-{}").format(sub_kwargs.cluster["cluster_type"]))

    # 存在性检查

    def precheck_for_instance_fix(self):
        for cluster_fix in self.data["infos"]:
            try:
                cluster = Cluster.objects.get(id=cluster_fix["cluster_id"], bk_biz_id=self.data["bk_biz_id"])
            except Cluster.DoesNotExist as e:
                raise Exception("redis cluster does not exist,{}", e)
            # check proxy
            for proxy in cluster_fix.get("proxy", []):
                if not cluster.proxyinstance_set.filter(machine__ip=proxy["ip"]):
                    raise Exception("proxy {} does not exist in cluster {}", proxy["ip"], cluster.immute_domain)
            # check slave
            for slave in cluster_fix.get("redis_slave", []):
                if not cluster.storageinstance_set.filter(
                    machine__ip=slave["ip"], instance_role=InstanceRole.REDIS_SLAVE.value
                ):
                    raise Exception("slave {} does not exist in cluster {}", slave["ip"], cluster.immute_domain)
