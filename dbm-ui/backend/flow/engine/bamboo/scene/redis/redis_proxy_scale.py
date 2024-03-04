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
from dataclasses import asdict
from typing import Any, Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta import api
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Machine
from backend.db_services.redis.util import is_twemproxy_proxy_type
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigFileEnum, ConfigTypeEnum, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    AccessManagerAtomJob,
    ProxyBatchInstallAtomJob,
    ProxyUnInstallAtomJob,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.ticket.constants import SwitchConfirmType, TicketType

logger = logging.getLogger("flow")


class RedisProxyScaleFlow(object):
    """
    proxy扩缩容流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __up_pre_check(self, new_ips):
        if len(set(new_ips)) != len(new_ips):
            raise Exception("have ip address has been used multiple times.")
        m = Machine.objects.filter(ip__in=new_ips).values("ip")
        if len(m) != 0:
            raise Exception("[{}] is used.".format(m))

    def __down_pre_check(self, old_ips, target_proxy_count):
        if target_proxy_count < 2:
            raise Exception("target_proxy_count is {} < 2".format(target_proxy_count))
        if len(old_ips) == 0:
            raise Exception("old ips len <= target_proxy_count {}".format(target_proxy_count))

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        cluster_info = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)[0]
        cluster_name = cluster_info["name"]
        cluster_type = cluster_info["cluster_type"]
        redis_master_set = cluster_info["redis_master_set"]
        redis_slave_set = cluster_info["redis_slave_set"]
        proxy_port = cluster_info["twemproxy_ports"][0]
        servers = []
        if is_twemproxy_proxy_type(cluster_type):
            for set in redis_master_set:
                ip_port, seg_range = str.split(set)
                servers.append("{} {} {} {}".format(ip_port, cluster_name, seg_range, 1))
        else:
            servers = redis_master_set + redis_slave_set

        return {
            "proxy_port": proxy_port,
            "cluster_type": cluster_type,
            "cluster_name": cluster_name,
            "bk_cloud_id": cluster_info["bk_cloud_id"],
            "servers": servers,
            "immute_domain": cluster_info["clusterentry_set"]["dns"][0]["domain"],
        }

    @staticmethod
    def __get_cluster_config(bk_biz_id: int, namespace: str, domain_name: str, db_version: str) -> Any:
        passwd_ret = PayloadHandler.redis_get_password_by_domain(domain_name)
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.CLUSTER,
                "level_value": domain_name,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": db_version,
                "conf_type": ConfigTypeEnum.ProxyConf,
                "namespace": namespace,
                "format": FormatType.MAP,
            }
        )
        if passwd_ret.get("redis_password"):
            data["content"]["redis_password"] = passwd_ret.get("redis_password")
        if passwd_ret.get("redis_proxy_password"):
            data["content"]["password"] = passwd_ret.get("redis_proxy_password")
        if passwd_ret.get("redis_proxy_admin_password"):
            data["content"]["redis_proxy_admin_password"] = passwd_ret.get("redis_proxy_admin_password")
        return data["content"]

    def redis_proxy_scale_up_flow(self):
        """
        扩容流程：
            0、获取信息(proxy配置、密码、端口、分片信息)(需要区分twemproxy和predixy)
            1、初始化信息
            2、下发介质包
            3、新增proxy
                3.1 部署实例
                3.2 元数据
                3.3 域名
                3.4 cc模块
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            proxy_ips = []
            for proxy_info in info["proxy"]:
                proxy_ips.append(proxy_info["ip"])

            self.__up_pre_check(proxy_ips)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], info["cluster_id"])
            if cluster_info["cluster_type"] in [
                ClusterType.TendisTwemproxyRedisInstance.value,
                ClusterType.TwemproxyTendisSSDInstance.value,
            ]:
                proxy_version = ConfigFileEnum.Twemproxy
            else:
                proxy_version = ConfigFileEnum.Predixy

            config_info = self.__get_cluster_config(
                self.data["bk_biz_id"], cluster_info["cluster_type"], cluster_info["immute_domain"], proxy_version
            )

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            cluster_tpl = {**cluster_info, "bk_biz_id": self.data["bk_biz_id"], "created_by": self.data["created_by"]}
            act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]

            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            # 安装proxy子流程
            sub_proxy_pipelines = []
            params = {
                "redis_pwd": config_info["redis_password"],
                "proxy_pwd": config_info["password"],
                "proxy_port": cluster_info["proxy_port"],
                "servers": cluster_info["servers"],
                "conf_configs": config_info,
                "spec_id": info["resource_spec"]["proxy"]["id"],
                "spec_config": info["resource_spec"]["proxy"],
            }
            # 如果从config_info中取出了admin_pwd，则说明是predixy，需要补充进params
            if proxy_version == ConfigFileEnum.Predixy:
                if "predixy_admin_passwd" in config_info and config_info["predixy_admin_passwd"]:
                    params["proxy_admin_pwd"] = config_info["predixy_admin_passwd"]
                else:
                    # 集群架构是predixy，但是之前没有管理密码，默认跟读写密码一样
                    params["proxy_admin_pwd"] = config_info["password"]
            for proxy_info in info["proxy"]:
                ip = proxy_info["ip"]
                act_kwargs.cluster = copy.deepcopy(cluster_tpl)

                params["ip"] = ip
                sub_builder = ProxyBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params)
                sub_proxy_pipelines.append(sub_builder)
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_proxy_pipelines)

            act_kwargs.cluster = {
                "proxy_ips": proxy_ips,
                "proxy_port": cluster_info["proxy_port"],
                "meta_func_name": RedisDBMeta.proxy_add_cluster.__name__,
                "domain_name": cluster_info["immute_domain"],
            }
            sub_pipeline.add_act(
                act_name=_("proxy加入集群元数据"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

            params = {
                "cluster_id": info["cluster_id"],
                "port": cluster_info["proxy_port"],
                "add_ips": proxy_ips,
                "op_type": DnsOpType.CREATE,
            }
            access_sub_builder = AccessManagerAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("{}新增proxy实例").format(cluster_info["cluster_name"]))
            )

        redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)
        redis_pipeline.run_pipeline()

    @staticmethod
    def __scale_down_cluster_info(bk_biz_id: int, cluster_id: int, target_proxy_count: int) -> dict:
        cluster_info = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)[0]
        cluster_name = cluster_info["name"]
        cluster_type = cluster_info["cluster_type"]
        proxy_port = cluster_info["twemproxy_ports"][0]
        proxy_ips = cluster_info["twemproxy_ips_set"]

        # 统计proxy的idc情况
        idc_ips = defaultdict(list)
        max_count = 0
        for proxy_ip in proxy_ips:
            m = Machine.objects.get(bk_biz_id=bk_biz_id, ip=proxy_ip)
            proxy_bk_idc_id = m.bk_idc_id
            idc_ips[proxy_bk_idc_id].append(proxy_ip)
            if len(idc_ips[proxy_bk_idc_id]) > max_count:
                max_count = len(idc_ips[proxy_bk_idc_id])
        idc_ips_dict = dict(idc_ips)

        # 计算需要裁撤的proxy列表。大概就是从多的pop出来
        proxy_now_count = len(proxy_ips)
        scale_down_ips = []
        while proxy_now_count > target_proxy_count:
            for idc in idc_ips_dict:
                idc_ips = idc_ips_dict[idc]
                if len(idc_ips) == max_count:
                    ip = idc_ips.pop()
                    scale_down_ips.append(ip)
                    proxy_now_count -= 1
                if proxy_now_count <= target_proxy_count:
                    break
            max_count -= 1

        return {
            "proxy_port": proxy_port,
            "cluster_type": cluster_type,
            "cluster_name": cluster_name,
            "scale_down_ips": scale_down_ips,
            "bk_cloud_id": cluster_info["bk_cloud_id"],
            "immute_domain": cluster_info["clusterentry_set"]["dns"][0]["domain"],
        }

    def redis_proxy_scale_down_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            cluster_info = self.__scale_down_cluster_info(
                self.data["bk_biz_id"], info["cluster_id"], info["target_proxy_count"]
            )
            cluster_tpl = {**cluster_info, "bk_biz_id": self.data["bk_biz_id"]}
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
            act_kwargs.exec_ip = cluster_info["scale_down_ips"]
            act_kwargs.cluster = {**cluster_info}

            self.__down_pre_check(cluster_info["scale_down_ips"], info["target_proxy_count"])

            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )
            if info["online_switch_type"] == SwitchConfirmType.USER_CONFIRM.value:
                sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

            params = {
                "cluster_id": info["cluster_id"],
                "port": cluster_info["proxy_port"],
                "del_ips": cluster_info["scale_down_ips"],
                "op_type": DnsOpType.RECYCLE_RECORD,
            }
            access_sub_builder = AccessManagerAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipeline.add_sub_pipeline(sub_flow=access_sub_builder)

            proxy_down_pipelines = []
            for proxy_ip in cluster_info["scale_down_ips"]:
                act_kwargs.cluster = copy.deepcopy(cluster_tpl)
                params = {"ip": proxy_ip, "proxy_port": cluster_info["proxy_port"]}
                sub_builder = ProxyUnInstallAtomJob(self.root_id, self.data, act_kwargs, params)
                proxy_down_pipelines.append(sub_builder)
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=proxy_down_pipelines)
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("{}卸载proxy实例").format(cluster_info["cluster_name"]))
            )

        redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)
        redis_pipeline.run_pipeline()

    def redis_proxy_scale_flow(self):
        if self.data["ticket_type"] == TicketType.REDIS_PROXY_SCALE_DOWN.value:
            self.redis_proxy_scale_down_flow()
        else:
            self.redis_proxy_scale_up_flow()
