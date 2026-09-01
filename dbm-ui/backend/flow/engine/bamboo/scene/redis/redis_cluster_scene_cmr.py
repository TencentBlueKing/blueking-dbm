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
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.redis.redis_modules.util import get_cluster_redis_modules_detail
from backend.db_services.redis.util import is_predixy_proxy_type, is_twemproxy_proxy_type
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigFileEnum, ConfigTypeEnum, DnsOpType, SyncType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    AccessManagerAtomJob,
    ClusterPredixyConfigServersRewriteAtomJob,
    ProxyBatchInstallAtomJob,
    ProxyUnInstallAtomJob,
    RedisClusterMasterReplaceJob,
    RedisClusterSlaveReplaceJob,
    RedisInstanceSlaveReplaceJob,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_submit_backup_ticket import (
    DEFAULT_AUTO_TERMINATE_SECONDS,
    RedisSubmitBackupTicketComponent,
)
from backend.flow.plugins.components.collections.redis.redis_update_version import RedisUpdateVersionComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import async_get_multi_cluster_info_by_cluster_ids

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
            ### "cluster_id": 1, # 用cluster_ids替换掉(2024-07-04)
            "cluster_ids":[], # 用于支持主从集群模式
            "proxy": [
                   {"ip": "1.1.1.a","spec_id": 17,
                  "target": {"bk_cloud_id": 0,"bk_host_id": 216,"status": 1,"ip": "2.2.2.b"}
                  }],
            "redis_slave": [
                 {"ip": "1.1.1.a","spec_id": 17,
                  "target": {"bk_cloud_id": 0,"bk_host_id": 216,"status": 1,"ip": "2.2.2.b"}
                 }],
            "redis_master": [
                {"ip": "1.1.1.c","spec_id": 17,
                  "target": {
                      "master": {"bk_cloud_id": 0,"bk_host_id": 195,"status": 1,"ip": "2.2.2.b"},
                      "slave": {"bk_cloud_id": 0,"bk_host_id": 187,"status": 1,"ip": "3.3.3.x"}}
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
        self.cluster_cache = {}

    @staticmethod
    def _build_cmr_cluster_info(base_info: dict) -> dict:
        """将 get_cluster_info_by_cluster_id 返回值转换为 CMR 场景所需结构."""
        cluster_id = base_info["cluster_id"]
        cluster_detail = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)[0]
        redis_master_set, redis_slave_set = cluster_detail["redis_master_set"], cluster_detail["redis_slave_set"]
        if is_twemproxy_proxy_type(base_info["cluster_type"]):
            servers = []
            for set in redis_master_set:
                ip_port, seg_range = str.split(set)
                servers.append("{} {} {} {}".format(ip_port, base_info["cluster_name"], seg_range, 1))
        else:
            servers = redis_master_set + redis_slave_set

        return {
            "immute_domain": base_info["immute_domain"],
            "bk_biz_id": base_info["bk_biz_id"],
            "bk_cloud_id": base_info["bk_cloud_id"],
            "cluster_type": base_info["cluster_type"],
            "cluster_name": base_info["cluster_name"],
            "cluster_id": base_info["cluster_id"],
            "slave_ports": base_info["slave_ports"],
            "master_ports": base_info["master_ports"],
            "ins_pair_map": base_info["master_ins_to_slave_ins"],
            "slave_ins_map": base_info["slave_ins_to_master_ins"],
            "slave_master_map": base_info["slave_ip_to_master_ip"],
            "master_slave_map": base_info["master_ip_to_slave_ip"],
            "proxy_port": base_info["proxy_port"],
            "proxy_ips": base_info["proxy_ips"],
            "db_version": base_info["major_version"],
            "backend_servers": servers,
        }

    def _prefetch_cluster_cache(self, cluster_ids: List[int]):
        missing_ids = [cid for cid in cluster_ids if cid not in self.cluster_cache]
        if not missing_ids:
            return
        base_infos = async_get_multi_cluster_info_by_cluster_ids(cluster_ids=missing_ids)
        for cluster_id in missing_ids:
            if str(base_infos[cluster_id]["bk_biz_id"]) != str(self.data["bk_biz_id"]):
                raise Exception(
                    _("redis cluster {} does not exist in bk_biz_id {}").format(cluster_id, self.data["bk_biz_id"])
                )
            self.cluster_cache[cluster_id] = self._build_cmr_cluster_info(base_infos[cluster_id])

    def get_cluster_info(self, cluster_id: int) -> dict:
        """获取集群现有信息 (优先读 prefetch 缓存)."""
        if cluster_id not in self.cluster_cache:
            self._prefetch_cluster_cache([cluster_id])
        return self.cluster_cache[cluster_id]

    @staticmethod
    def __get_cluster_config(bk_biz_id: int, namespace: str, domain_name: str, db_version: str) -> Any:
        """
        获取已部署的实例配置
        """
        passwd_ret = PayloadHandler.redis_get_password_by_domain(domain_name)
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

        data["content"]["redis_password"] = passwd_ret.get("redis_password")
        data["content"]["password"] = passwd_ret.get("redis_proxy_password")
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
    def complete_machine_replace(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS-整机替换"))
        sub_pipelines, cluster_ids = [], []
        has_storage_replacement = False
        unique_cluster_ids = {
            int(cluster_id)
            for cluster_replacement in self.data["infos"]
            for cluster_id in cluster_replacement["cluster_ids"]
        }
        cluster_ids = list(unique_cluster_ids)
        self._prefetch_cluster_cache(cluster_ids)

        for cluster_replacement in self.data["infos"]:
            if cluster_replacement.get("redis_master") or cluster_replacement.get("redis_slave"):
                has_storage_replacement = True
            if len(cluster_replacement["cluster_ids"]) > 1:
                # 单机多实例，主从架构的整机替换单据
                sub_pipeline = self.generate_single_replacement(self.data, deepcopy(act_kwargs), cluster_replacement)
                sub_pipelines.append(sub_pipeline)
            else:
                for cluster_id in cluster_replacement["cluster_ids"]:
                    cluster_kwargs = deepcopy(act_kwargs)
                    cluster_info = self.get_cluster_info(cluster_id)
                    sync_type = SyncType.SYNC_MMS.value  # ssd sync from master
                    if cluster_info["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value:
                        sync_type = SyncType.SYNC_SMS.value

                    flow_data = self.data
                    cluster_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]  # 海外多云区域
                    cluster_kwargs.cluster.update(cluster_info)
                    cluster_kwargs.cluster["created_by"] = self.data["created_by"]
                    flow_data["sync_type"] = sync_type
                    flow_data["replace_info"] = cluster_replacement

                    sub_pipeline = self.generate_cluster_replacement(flow_data, cluster_kwargs, cluster_replacement)
                    sub_pipelines.append(sub_pipeline)

        if len(sub_pipelines) > 0:
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
            # 仅在涉及存储节点(master/slave)替换时，自动提交一张 Redis 备份单据（3 小时后未执行自动终止）
            if has_storage_replacement:
                redis_pipeline.add_act(
                    act_name=_("自动提交Redis备份单据"),
                    act_component_code=RedisSubmitBackupTicketComponent.code,
                    kwargs={
                        "cluster_ids": cluster_ids,
                        "bk_biz_id": self.data["bk_biz_id"],
                        "created_by": self.data.get("created_by"),
                        "backup_target": "slave",
                        "backup_type": "normal_backup",
                        "auto_terminate_seconds": DEFAULT_AUTO_TERMINATE_SECONDS,
                        "parent_ticket_id": self.data.get("uid"),
                        "remark": _("整机替换完成后自动提交备份单据"),
                    },
                )
        # return redis_pipeline.run_pipeline()
        return redis_pipeline.run_pipeline_with_sidecar(check_ai_monitor_cluster_list=cluster_ids)

    @staticmethod
    def _split_ip_port(item):
        """从 "ip:port" 或 "ip:port seg_range" 中拆出 (ip, int(port))"""
        ip, port = item.split()[0].split(":")
        return ip, int(port)

    def _build_clusters_instance_map(self, cluster_ids):
        """
        聚合本单据下所有主从集群的实例信息，返回字典。
        tendis_cluster 返回的 *_set 元素为 "ip:port" 或 "ip:port seg_range"。
        """
        clusters_detail = api.cluster.nosqlcomm.other.get_clusters_details(cluster_ids)

        info = {
            "master_ports": {},  # master ip -> [port1, port2, ...]
            "slave_ports": {},  # slave ip -> [port1, port2, ...]
            # 实例/IP 主从映射
            "ins_pair_map": {},  # master ip:port -> slave ip:port
            "slave_ins_map": {},  # slave ip:port -> master ip:port
            "master_slave_map": {},  # master ip -> slave ip
            "slave_master_map": {},  # slave ip -> master ip
            # master 实例(ip:port) -> 所属集群
            "master_cid_relation": {},
        }

        for cluster_detail in clusters_detail:
            for m_item, s_item in zip(cluster_detail["redis_master_set"], cluster_detail["redis_slave_set"]):
                m_ip, m_port = self._split_ip_port(m_item)
                s_ip, s_port = self._split_ip_port(s_item)
                m_ip_port = "{}:{}".format(m_ip, m_port)
                s_ip_port = "{}:{}".format(s_ip, s_port)

                info["master_ports"].setdefault(m_ip, []).append(m_port)
                info["slave_ports"].setdefault(s_ip, []).append(s_port)
                info["ins_pair_map"][m_ip_port] = s_ip_port
                info["slave_ins_map"][s_ip_port] = m_ip_port
                info["master_slave_map"][m_ip] = s_ip
                info["slave_master_map"][s_ip] = m_ip
                # master 实例 -> 所属集群
                info["master_cid_relation"][m_ip_port] = cluster_detail

        return clusters_detail, info

    # 单机多实例, 并行
    def generate_single_replacement(self, flow_data, act_kwargs, replacement_param):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)
        act_kwargs.cluster["created_by"] = self.data["created_by"]
        act_kwargs.cluster["sync_type"] = SyncType.SYNC_MMS.value
        # 提取本单据下所有主从集群的集群信息与实例信息
        cluster_ids = replacement_param["cluster_ids"]
        clusters_detail, ins_info = self._build_clusters_instance_map(cluster_ids)

        # 以第一个集群为基准，回填集群元信息（bk_cloud_id/immute_domain 等）
        base_info = clusters_detail[0]
        act_kwargs.bk_cloud_id = base_info["bk_cloud_id"]  # 海外多云区域
        act_kwargs.cluster.update(
            {
                "bk_biz_id": base_info["bk_biz_id"],
                "bk_cloud_id": base_info["bk_cloud_id"],
                "cluster_id": base_info["id"],
                "cluster_name": base_info["name"],
                "immute_domain": base_info["immute_domain"],
                "cluster_type": base_info["cluster_type"],
                "major_version": base_info["major_version"],
                "db_version": base_info["major_version"],
                "region": base_info["region"],
            }
        )
        act_kwargs.cluster.update(ins_info)
        act_kwargs.cluster["cluster_ids"] = list(map(int, cluster_ids))

        sub_pipeline.add_act(
            act_name=_("初始化-{}".format(cluster_ids)),
            act_component_code=GetRedisActPayloadComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 先添加 Slave 替换流程
        redis_slave = replacement_param.get("redis_slave")
        if redis_slave:
            slave_kwargs = deepcopy(act_kwargs)
            slave_target = redis_slave[0].get("target", {})
            slave_replace_pipe = RedisInstanceSlaveReplaceJob(
                self.root_id,
                flow_data,
                slave_kwargs,
                {
                    "redis_slave": redis_slave,
                    "slave_spec": slave_target.get("spec", {}),
                },
            )
            sub_pipeline.add_sub_pipeline(slave_replace_pipe)

        # 最后添加 Master 替换流程, reget proxy info.
        redis_master = replacement_param.get("redis_master")
        if redis_master:
            master_kwargs = deepcopy(act_kwargs)
            master_target = redis_master[0].get("target", {})
            master_replace_pipe = RedisClusterMasterReplaceJob(
                self.root_id,
                flow_data,
                master_kwargs,
                {
                    "redis_master": redis_master,
                    "master_spec": master_target.get("master", {}).get("spec", {}),
                    "slave_spec": master_target.get("slave", {}).get("spec", {}),
                },
            )
            sub_pipeline.add_sub_pipeline(master_replace_pipe)

        version_acts = []
        for cluster_detail in clusters_detail:
            version_kwargs = deepcopy(act_kwargs)
            version_kwargs.cluster["cluster_id"] = cluster_detail["id"]
            version_kwargs.cluster["immute_domain"] = cluster_detail["immute_domain"]
            version_kwargs.cluster["update_storage"] = True
            version_acts.append(
                {
                    "act_name": _("{}-更新版本").format(cluster_detail["immute_domain"]),
                    "act_component_code": RedisUpdateVersionComponent.code,
                    "kwargs": asdict(version_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=version_acts)

        return sub_pipeline.build_sub_process(sub_name=_("整机替换-{}").format(act_kwargs.cluster["immute_domain"]))

    # 组装&控制 集群替换流程
    def generate_cluster_replacement(self, flow_data, act_kwargs, replacement_param):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)

        sub_pipeline.add_act(
            act_name=_("初始化-{}".format(act_kwargs.cluster["immute_domain"])),
            act_component_code=GetRedisActPayloadComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 先添加Slave替换流程
        if replacement_param.get("redis_slave"):
            slave_kwargs = deepcopy(act_kwargs)
            slave_replace_pipe = RedisClusterSlaveReplaceJob(
                self.root_id,
                flow_data,
                slave_kwargs,
                {
                    "redis_slave": replacement_param.get("redis_slave"),
                    "slave_spec": replacement_param.get("redis_slave")[0].get("target", {}).get("spec", {}),
                },
            )
            sub_pipeline.add_sub_pipeline(slave_replace_pipe)

        # 再添加Proxy替换流程
        if replacement_param.get("proxy"):
            proxy_kwargs = deepcopy(act_kwargs)
            self.proxy_replacement(
                sub_pipeline,
                proxy_kwargs,
                {
                    "proxy": replacement_param.get("proxy"),
                    "proxy_spec": replacement_param.get("proxy")[0].get("target", {}).get("spec", {}),
                },
            )

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
                self.root_id,
                flow_data,
                master_kwargs,
                {
                    "redis_master": replacement_param.get("redis_master"),
                    "master_spec": replacement_param.get("redis_master")[0]
                    .get("target", {})
                    .get("master", {})
                    .get("spec", {}),
                    "slave_spec": replacement_param.get("redis_master")[0]
                    .get("target", {})
                    .get("slave", {})
                    .get("spec", {}),
                },
            )
            sub_pipeline.add_sub_pipeline(master_replace_pipe)

        act_kwargs.cluster["update_all"] = True
        sub_pipeline.add_act(
            act_name=_("{}-更新版本").format(act_kwargs.cluster["immute_domain"]),
            act_component_code=RedisUpdateVersionComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 仅在master/slave(存储节点)替换时，predixy类型的集群需要在流程结束前执行config rewrite
        if replacement_param.get("redis_master") or replacement_param.get("redis_slave"):
            if is_predixy_proxy_type(act_kwargs.cluster["cluster_type"]):
                # 在所有predixy节点上执行config rewrite
                predixy_conf_rewrite_builder = ClusterPredixyConfigServersRewriteAtomJob(
                    self.root_id,
                    flow_data,
                    act_kwargs,
                    {
                        "cluster_domain": act_kwargs.cluster["immute_domain"],
                        "to_remove_servers": [],  # 整机替换场景不需要移除特定servers
                    },
                )
                if predixy_conf_rewrite_builder:
                    sub_pipeline.add_sub_pipeline(sub_flow=predixy_conf_rewrite_builder)

        return sub_pipeline.build_sub_process(sub_name=_("整机替换-{}").format(act_kwargs.cluster["immute_domain"]))

    def proxy_replacement(self, sub_pipeline, proxy_kwargs, proxy_replace_info):
        act_kwargs = copy.deepcopy(proxy_kwargs)
        del act_kwargs.cluster["slave_ports"]
        del act_kwargs.cluster["master_ports"]
        del act_kwargs.cluster["ins_pair_map"]
        del act_kwargs.cluster["slave_ins_map"]
        del act_kwargs.cluster["slave_master_map"]
        del act_kwargs.cluster["master_slave_map"]

        old_proxies, new_proxies = [], []
        proxy_replace_details = proxy_replace_info["proxy"]
        for replace_link in proxy_replace_details:
            # {"ip": "1.1.1.a","spec_id": 17,"target": {"bk_cloud_id": 0,"bk_host_id": 216,"status": 1,"ip": "2.2.2.b"}}
            old_proxies.append(replace_link["ip"])
            new_proxies.append(replace_link["target"]["ip"])

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
        module_rows = get_cluster_redis_modules_detail(cluster_id=act_kwargs.cluster["cluster_id"])
        load_modules = [module_row["module_name"] for module_row in module_rows]

        for proxy_ip in new_proxies:
            replace_kwargs = copy.deepcopy(act_kwargs)
            params = {
                "ip": proxy_ip,
                "redis_pwd": config_info["redis_password"],
                "proxy_pwd": config_info["password"],
                "conf_configs": config_info,
                "proxy_admin_pwd": config_info["redis_proxy_admin_password"],
                "proxy_port": int(config_info["port"]),
                "servers": replace_kwargs.cluster["backend_servers"],
                "spec_id": proxy_replace_info["proxy_spec"].get("id", 0),
                "spec_config": proxy_replace_info["proxy_spec"],
            }
            sub_builder = ProxyBatchInstallAtomJob(
                self.root_id, self.data, replace_kwargs, params, load_modules=load_modules
            )
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
        # 第三步：接入层管理：清理旧接入层(这里可能需要留点时间然后在执行下一步)
        params = {
            "cluster_id": act_kwargs.cluster["cluster_id"],
            "port": act_kwargs.cluster["proxy_port"],
            "del_ips": old_proxies,
            "op_type": DnsOpType.RECYCLE_RECORD.value,
            # CLB延迟删除行为
            "clb_delay_delete": True,
        }
        access_sub_builder = AccessManagerAtomJob(self.root_id, self.data, act_kwargs, params)
        if access_sub_builder:
            sub_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)

        # 第四步：人工确认
        sub_pipeline.add_act(act_name=_("旧Proxy下架-等待确认"), act_component_code=PauseComponent.code, kwargs={})

        # 真正下架CLB
        params = {
            "cluster_id": act_kwargs.cluster["cluster_id"],
            "port": act_kwargs.cluster["proxy_port"],
            "del_ips": old_proxies,
            "op_type": DnsOpType.RECYCLE_RECORD.value,
            # CLB延迟删除行为
            "clb_delay_delete": False,
            "only_cluster_entry_type": ClusterEntryType.CLB.value,
        }
        access_sub_builder = AccessManagerAtomJob(self.root_id, self.data, act_kwargs, params)
        if access_sub_builder:
            sub_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)

        # 第四步：卸载Proxy
        proxy_down_pipelines = []
        for proxy_ip in old_proxies:
            params = {"ip": proxy_ip, "proxy_port": act_kwargs.cluster["proxy_port"]}
            uninstall_kwargs = copy.deepcopy(act_kwargs)
            sub_builder = ProxyUnInstallAtomJob(self.root_id, self.data, uninstall_kwargs, params)
            proxy_down_pipelines.append(sub_builder)
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=proxy_down_pipelines)

    # 存在性检查
    def precheck_for_compelete_replace(self):
        for cluster_replacement in self.data["infos"]:
            for cluster_id in cluster_replacement["cluster_ids"]:
                try:
                    cluster = Cluster.objects.prefetch_related(
                        "proxyinstance_set",
                        "storageinstance_set",
                        "proxyinstance_set__machine",
                        "storageinstance_set__machine",
                    ).get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
                except Cluster.DoesNotExist as e:
                    raise Exception("redis cluster does not exist,{}", e)
                existing_proxy_ips = {p.machine.ip for p in cluster.proxyinstance_set.all()}
                existing_slave_ips = set()
                existing_master_ips = set()
                for inst in cluster.storageinstance_set.all():
                    if inst.instance_role == InstanceRole.REDIS_SLAVE.value:
                        existing_slave_ips.add(inst.machine.ip)
                    elif inst.instance_role == InstanceRole.REDIS_MASTER.value:
                        existing_master_ips.add(inst.machine.ip)
                # check proxy
                for proxy in cluster_replacement.get("proxy", []):
                    if proxy["ip"] not in existing_proxy_ips:
                        raise Exception("proxy {} does not exist in cluster {}", proxy["ip"], cluster.immute_domain)
                # check slave
                for slave in cluster_replacement.get("redis_slave", []):
                    if slave["ip"] not in existing_slave_ips:
                        raise Exception("slave {} does not exist in cluster {}", slave["ip"], cluster.immute_domain)
                # check master
                for master in cluster_replacement.get("redis_master", []):
                    if master["ip"] not in existing_master_ips:
                        raise Exception("master {} does not exist in cluster {}", master["ip"], cluster.immute_domain)
