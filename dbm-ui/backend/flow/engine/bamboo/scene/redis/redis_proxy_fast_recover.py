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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType, RedisFastRecoverEnum
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import AccessManagerAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisProxyFastRecoverFlow(object):
    """
    园区故障时的快速业务恢复
    1. 功能一: 提供一批IP, 踢掉接入层; 可选是否重启proxy实例
    2. 功能二: 提供一批IP, 重新加入接入层 (兼容,被DBHA踢掉的IP修复)

    {
        "bk_biz_id": 3,
        "uid": "2025111310000",
        "created_by":"vitox",
        "ticket_type":"REDIS_PROXY_FAST_FIX", #TicketType.REDIS_PROXY_FAST_FIX.value
        "infos": [
            {
            "cluster_id": 1,
            "proxy": [
                        {"ip": "1.1.1.a","bk_cloud_id": 0},
                    ],
            # 可选值: PROXY_ENTRY_KICKOFF(踢掉集群入口); PROXY_ENTRY_FIX(修复集群入口)
            "operate_type":"PROXY_ENTRY_KICKOFF",
            "restart_proxy": False, # 默认值
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
        self.precheck_for_fast_recovery()

    def __init_builder(self, operate_name: str):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster["operate"] = operate_name
        return redis_pipeline, act_kwargs

    # 这里整理快速恢复所需要的参数, 主入口
    def cluster_proxy_fast_recovery(self):
        redis_pipeline, act_kwargs = self.__init_builder(_("PROXY-快速恢复"))

        redis_pipeline.add_act(
            act_name=_("初始化"),
            act_component_code=GetRedisActPayloadComponent.code,
            kwargs=asdict(act_kwargs),
        )

        all_proxies = []
        for op_cls in self.data["infos"]:
            all_proxies.extend([proxy["ip"] for proxy in op_cls["proxy"]])

        acts_list, max_batch, batch_ips, batch_seq = [], 150, [], 0
        for ip in all_proxies:
            batch_ips.append(ip)
            if len(batch_ips) < max_batch:
                continue
            else:
                batch_seq += 1
                act_kwargs.exec_ip = copy.deepcopy(batch_ips)
                acts_list.append(
                    {
                        "act_name": _("第{}批-下发介质").format(batch_seq),
                        "act_component_code": TransFileComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
                batch_ips = []
        if len(batch_ips) > 0:
            batch_seq += 1
            act_kwargs.exec_ip = copy.deepcopy(batch_ips)
            acts_list.append(
                {
                    "act_name": _("第{}批-下发介质").format(batch_seq),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        if acts_list:
            redis_pipeline.add_parallel_acts(acts_list=acts_list)

        sub_pipelines = []
        for op_cls in self.data["infos"]:
            cluster = Cluster.objects.filter(id=op_cls["cluster_id"]).get()
            act_kwargs.cluster["bk_biz_id"] = cluster.bk_biz_id
            act_kwargs.cluster["bk_cloud_id"] = cluster.bk_cloud_id
            act_kwargs.cluster["cluster_id"] = cluster.id
            act_kwargs.cluster["proxy_port"] = cluster.proxyinstance_set.first().port
            act_kwargs.cluster["cluster_type"] = cluster.cluster_type
            act_kwargs.cluster["immute_domain"] = cluster.immute_domain
            op_proxies = [proxy["ip"] for proxy in op_cls["proxy"]]

            # 入口 1 ； 把被踢掉了的proxies 加入回接入层 （包含dhba踢掉的、dba人工踢掉的）
            if (
                op_cls.get(
                    "operate_type",
                )
                == RedisFastRecoverEnum.PROXY_ENTRY_FIX.value
            ):
                logger.info("proxy fix 4 {}:{}".format(cluster.immute_domain, op_proxies))
                sub_pipelines.append(self.handle_proxy_entry_fix(act_kwargs, cluster, op_proxies))
            # 入口 2 ； 踢掉故障园区、故障节点 的接入层； 可选是否需要重启proxy
            elif (
                op_cls.get(
                    "operate_type",
                )
                == RedisFastRecoverEnum.PROXY_ENTRY_KICKOFF.value
            ):
                logger.info("proxy kickoff 4 {}:{}".format(cluster.immute_domain, op_proxies))
                sub_pipelines.append(
                    self.handle_proxy_entry_kickoff(act_kwargs, op_cls.get("restart_proxy", False), op_proxies)
                )
            else:
                raise Exception(
                    "redis proxy operate_type does not support,{}",
                    op_cls.get(
                        "operate_type",
                    ),
                )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        return redis_pipeline.run_pipeline()

    # 入口 1 ； 把被踢掉了的proxies 加入回接入层 （包含dhba踢掉的、dba人工踢掉的）
    def handle_proxy_entry_fix(self, act_kwargs, cluster, op_proxies):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        reuse_acts = []  # 1. 重装proxy实例
        for proxy in op_proxies:
            reuse_kwargs = copy.deepcopy(act_kwargs)
            reuse_kwargs.cluster["proxy_reuse"] = True  # 这里会重置proxy的配置文件
            reuse_kwargs.cluster["proxy_ip"] = proxy
            reuse_kwargs.exec_ip = proxy
            reuse_kwargs.get_redis_payload_func = RedisActPayload.proxy_reuse_payload.__name__
            reuse_acts.append(
                {
                    "act_name": _("Proxy-{}-复用实例").format(proxy),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(reuse_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=reuse_acts)
        # 2. 检查集群所有proxy 的后端是否一致
        if cluster.cluster_type in [
            ClusterType.TwemproxyTendisSSDInstance,
            ClusterType.TendisTwemproxyRedisInstance,
        ]:
            one_proxy = cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING.value).first()
            act_kwargs.exec_ip = one_proxy.machine.ip
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_twemproxy_backends_4_scene.__name__
            sub_pipeline.add_act(
                act_name=_("{}-检查状态").format(act_kwargs.exec_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

        # 3. 重新加入 接入层 CLB、DNS、Polairs
        sub_pipeline.add_sub_pipeline(
            AccessManagerAtomJob(
                self.root_id,
                self.data,
                act_kwargs,
                {
                    "cluster_id": cluster.id,
                    "port": act_kwargs.cluster["proxy_port"],
                    "add_ips": op_proxies,
                    "op_type": DnsOpType.CREATE.value,
                },
            )
        )
        # 4. 修改元数据状态 ---> running
        act_kwargs.cluster.update(
            {
                "proxy_ips": op_proxies,
                "meta_update_status": InstanceStatus.RUNNING.value,
                "meta_func_name": RedisDBMeta.update_cluster_proxy_status.__name__,
            }
        )
        sub_pipeline.add_act(
            act_name=_("Proxy-更新元数据状态-{}".format(cluster.immute_domain)),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )
        return sub_pipeline.build_sub_process(sub_name=_("加入-PROXY"))

    # 入口 2 ； 踢掉故障园区、故障节点 的接入层； 可选是否需要重启proxy
    def handle_proxy_entry_kickoff(self, act_kwargs, restart_proxy: bool, op_proxies):
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        sub_pipeline.add_sub_pipeline(
            AccessManagerAtomJob(
                self.root_id,
                self.data,
                act_kwargs,
                {
                    "cluster_id": act_kwargs.cluster["cluster_id"],
                    "port": act_kwargs.cluster["proxy_port"],
                    "del_ips": op_proxies,
                    "op_type": DnsOpType.RECYCLE_RECORD.value,
                },
            )
        )
        # 2. 重启proxy 【可选】# 默认不重启proxy
        if restart_proxy:
            reuse_acts = []
            for proxy in op_proxies:
                reuse_kwargs = copy.deepcopy(act_kwargs)
                reuse_kwargs.cluster["proxy_reuse"] = False  # 这里会重置proxy的配置文件
                reuse_kwargs.cluster["proxy_ip"] = proxy
                reuse_kwargs.exec_ip = proxy
                reuse_kwargs.get_redis_payload_func = RedisActPayload.proxy_reuse_payload.__name__
                reuse_acts.append(
                    {
                        "act_name": _("Proxy-{}-重启实例").format(proxy),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(reuse_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=reuse_acts)

        # 3. 修改元数据状态 ---> running
        act_kwargs.cluster.update(
            {
                "proxy_ips": op_proxies,
                "meta_update_status": InstanceStatus.AVAILABLE.value,
                "meta_func_name": RedisDBMeta.update_cluster_proxy_status.__name__,
            }
        )
        sub_pipeline.add_act(
            act_name=_("Proxy-更新元数据状态-{}".format(act_kwargs.cluster["immute_domain"])),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(act_kwargs),
        )
        return sub_pipeline.build_sub_process(sub_name=_("踢掉-PROXY"))

    # 存在性检查
    def precheck_for_fast_recovery(self):
        for proxies_item in self.data["infos"]:
            try:
                cluster = Cluster.objects.prefetch_related(
                    "proxyinstance_set",
                    "proxyinstance_set__machine",
                ).get(id=proxies_item["cluster_id"], bk_biz_id=self.data["bk_biz_id"])
            except Cluster.DoesNotExist as e:
                raise Exception("redis cluster does not exist,{}", e)
            # check proxy
            for proxy in proxies_item.get("proxy", []):
                if not cluster.proxyinstance_set.filter(machine__ip=proxy["ip"]):
                    raise Exception("proxy {} does not exist in cluster {}", proxy["ip"], cluster.immute_domain)
