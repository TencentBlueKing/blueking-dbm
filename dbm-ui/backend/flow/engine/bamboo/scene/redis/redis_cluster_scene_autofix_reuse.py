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
import logging
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from typing import Any, Dict, Optional

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta import api
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_twemproxy_proxy_type
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ConfigTypeEnum, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import AccessManagerAtomJob
from backend.flow.plugins.components.collections.mysql.trans_file_with_retry import TransFileWithRetryComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaWithRetryKwargs
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisClusterAutoFixReuseSceneFlow(object):
    """
    tendis fault autofix 4 reuse hosts
    这里会尝试复用旧机器, 不需要新申请机器, 暂时先只支持Proxy类型
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"vitox",
        "ticket_type":"REDIS_CLUSTER_AUTOFIX_REUSE",
        "infos": [
            {
            "cluster_ids": [1,2],
            "proxy": [
                   {"ip": "1.1.1.a","spec_id": 17,
                  "target": {"bk_cloud_id": 0,"bk_host_id": 216,"status": 1,"ip": "2.2.2.b"}
                  }],
            }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    @staticmethod
    def get_cluster_info(bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群现有信息
        1. master 对应 slave 机器
        2. master 上的端口列表
        3. 实例对应关系：{master:port:slave:port}
        """
        cluster = Cluster.objects.prefetch_related(
            "proxyinstance_set",
            "storageinstance_set",
            "proxyinstance_set__machine",
            "storageinstance_set__machine",
            "storageinstance_set__as_ejector",
        ).get(id=cluster_id, bk_biz_id=bk_biz_id)

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
        if is_twemproxy_proxy_type(cluster.cluster_type):
            for set in redis_master_set:
                ip_port, seg_range = str.split(set)
                servers.append("{} {} {} {}".format(ip_port, cluster.name, seg_range, 1))
        else:
            servers = redis_master_set + redis_slave_set

        proxy_port, proxy_ips = 0, []
        if cluster.cluster_type != ClusterType.TendisRedisInstance.value:
            proxy_port = cluster.proxyinstance_set.first().port
            proxy_ips = [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()]

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
            "proxy_port": proxy_port,
            "proxy_ips": proxy_ips,
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

    def reuse_machine(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("REDIS-自愈复用"))
        sub_pipelines = []
        for cluster_fix in self.data["infos"]:
            for cluster_id in cluster_fix["cluster_ids"]:
                cluster_kwargs = deepcopy(act_kwargs)
                cluster_info = self.get_cluster_info(self.data["bk_biz_id"], cluster_id)
                flow_data = self.data
                cluster_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]  # 海外多云区域
                cluster_kwargs.cluster.update(cluster_info)
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

        # slave 的修复 - TODO

        # 尝试复用 proxy 机器
        # A: 1. 登陆机器 ; 2. 对比配置文件 ；3.拉起进程 ; 4. 修复接入层 ； 5. 修改元数据状态
        # B: 机器登陆超时，发起替换流程
        if fix_params.get("proxy"):
            sub_pipeline.add_sub_pipeline(
                self.proxy_reuse_fix(
                    act_kwargs,
                    {
                        "proxy": fix_params.get("proxy"),
                        "proxy_spec": fix_params.get("resource_spec", {}).get("proxy", {}),
                    },
                )
            )

        return sub_pipeline.build_sub_process(sub_name=_("故障自愈-{}").format(act_kwargs.cluster["immute_domain"]))

    # proxy 复用逻辑
    def proxy_reuse_fix(self, act_kwargs, proxy_fix_info):
        # sub_pipelines, reuse_pipeline = [], SubBuilder(root_id=self.root_id, data=self.data)
        for one_proxy in proxy_fix_info:
            proxy_ip = one_proxy["ip"]
            proxy_kwargs, sub_pipeline = deepcopy(act_kwargs), SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("尝试多次下发介质"),
                act_component_code=TransFileWithRetryComponent.code,
                kwargs=asdict(
                    DownloadMediaWithRetryKwargs(
                        bk_cloud_id=proxy_kwargs.bk_cloud_id,
                        exec_ip=proxy_ip,
                        file_list=GetFileList(db_type=DBType.Redis.value).get_db_actuator_package(),
                        retry_seconds=7200,
                    )
                ),
            )

            # 接入层重新注册
            sub_pipeline.add_sub_pipeline(
                sub_flow=AccessManagerAtomJob(
                    self.root_id,
                    self.data,
                    act_kwargs,
                    {
                        "cluster_id": act_kwargs.cluster["cluster_id"],
                        "port": act_kwargs.cluster["proxy_port"],
                        "add_ips": [proxy_ip],
                        "op_type": DnsOpType.CREATE.value,
                    },
                )
            )
