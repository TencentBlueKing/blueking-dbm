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
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Optional

from django.forms.models import model_to_dict
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import DestroyedStatus
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.db_services.redis.util import is_have_proxy
from backend.flow.consts import DBActuatorTypeEnum, RedisActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisBatchShutdownAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisDataStructureTaskDeleteFlow(object):
    """
    redis 构造删除
    {
      "bk_biz_id":3,
      "uid": "2022061612120001",
      "created_by":"admin",
      "ticket_type": "REDIS_DATA_STRUCTURE_TASK_DELETE",
      "infos":[
        {
             "related_rollback_bill_id":2022061612120001,
             "prod_cluster":"xxxx.xxxx.xxxx.xxxx",
             "bk_cloud_id":2
        }
      ]
      "skip_connections_check":False,
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_cluster_info(bk_biz_id: int, related_rollback_bill_id: int, prod_cluster: str) -> dict:
        """
        1、删除构造记录：需要提供哪些参数呢？ （bk_cloud_id，源集群名，记录id （related_rollback_bill_id））
        """

        task = (
            TbTendisRollbackTasks.objects.filter(
                related_rollback_bill_id=related_rollback_bill_id, bk_biz_id=bk_biz_id, prod_cluster=prod_cluster
            )
            .order_by("-update_at")
            .first()
        )

        if not task:
            raise Exception(
                "No rollback task found for bill_id={}, cluster={}, bk_biz_id={}".format(
                    related_rollback_bill_id, prod_cluster, bk_biz_id
                )
            )

        formatted_task = model_to_dict(task)
        for key, value in formatted_task.items():
            if isinstance(value, datetime):
                formatted_task[key] = value.strftime("%Y-%m-%d %H:%M:%S")

        return formatted_task

    def redis_rollback_task_delete_flow(self):
        """
        1、删除包含删除redis 实例的cmdb，下掉redis实例，下掉proxy实例，最后再更新构造记录为已销毁
        构造记录销毁需要元数据：
         1、master ip_ports 下架，元数据处理
         2、proxy下架
        """
        redis_pipeline_all = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines_multi_cluster = []
        for info in self.data["infos"]:
            sub_pipelines_multi_cluster.append(self.build_cluster_task_delete(info))
        redis_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines_multi_cluster)
        return redis_pipeline_all.run_pipeline()

    def build_cluster_task_delete(self, info: dict, tasks_info: dict = None):
        """Build a SubProcess for a single cluster's cleanup/delete steps.

        Can be embedded into another pipeline (e.g. rollback exercise)
        without spawning a separate FlowTree.

        Args:
            info: Cluster info dict from ticket data.
            tasks_info: Pre-computed task info dict. If None, queries TbTendisRollbackTasks.
        """
        ticket_bk_biz_id = self.data["bk_biz_id"]
        is_drill = self.data.get("is_rollback_drill", False)

        if tasks_info is None:
            tasks_info = self.__get_cluster_info(
                bk_biz_id=ticket_bk_biz_id,
                related_rollback_bill_id=info["related_rollback_bill_id"],
                prod_cluster=info["prod_cluster"],
            )

        logger.info("redis_rollback_task_delete_flow tasks_info:{}".format(tasks_info))
        redis_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **tasks_info,
            "operate": self.data["ticket_type"],
        }
        act_kwargs.cluster["cluster_type"] = act_kwargs.cluster["temp_cluster_type"]

        cluster_kwargs = deepcopy(act_kwargs)
        cluster_kwargs.cluster = {
            "related_rollback_bill_id": info["related_rollback_bill_id"],
            "bk_biz_id": ticket_bk_biz_id,
            "prod_cluster": info["prod_cluster"],
            "meta_func_name": RedisDBMeta.update_rollback_task_status.__name__,
            "cluster_type": cluster_kwargs.cluster["cluster_type"],
            "destroyed_status": DestroyedStatus.DESTROYING,
        }
        redis_pipeline.add_act(
            act_name=_("更新构造记录为销毁中"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(cluster_kwargs)
        )
        # 初始化
        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        master_ports = {}
        for instance in act_kwargs.cluster["temp_instance_range"]:
            ip, port = instance.split(":")
            if ip in master_ports:
                master_ports[ip].append(int(port))
            else:
                master_ports[ip] = [int(port)]
        act_kwargs.cluster["master_ports"] = master_ports

        # ### 下发工具包############################################################
        # 这里构造销毁的时候，如果缺失actuator，那么dbtools，dbmon估计也是没有了的，构造销毁需要一起下发
        acts_lists = []
        first_act_kwargs = deepcopy(act_kwargs)
        for ip_address, ports in master_ports.items():
            trans_files = GetFileList(db_type=DBType.Redis)
            first_act_kwargs.file_list = trans_files.redis_dbmon()
            first_act_kwargs.exec_ip = ip_address
            acts_lists.append(
                {
                    "act_name": _("Redis-{}-下发工具包").format(ip_address),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(first_act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_lists)
        # ### 下发工具包完成############################################################

        # #### 下架旧redis实例 #############################################################################
        sub_pipelines = []
        for ip_address, ports in master_ports.items():
            params = {
                "ip": ip_address,
                "ports": ports,
                "skip_connections_check": self.data.get("skip_connections_check", False),
                # 演练场景：dbmon从未安装，跳过重装/卸载监控步骤
                "skip_dbmon_uninstall": is_drill,
                # 数据构造删除等同集群下架，需通知actuator执行集群级下架逻辑
                "is_cluster_shutdown": True,
            }
            sub_builder = RedisBatchShutdownAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # #### 下架旧proxy实例 #############################################################################
        # 重新赋值，因为下架redis时cluster会被赋值
        # act_kwargs.cluster = {**tasks_info}
        act_kwargs.cluster["cluster_type"] = act_kwargs.cluster["temp_cluster_type"]
        if is_have_proxy(act_kwargs.cluster["cluster_type"]):
            act_kwargs.cluster["operate"] = (
                DBActuatorTypeEnum.Proxy.value + "_" + RedisActuatorActionEnum.Shutdown.value
            )
            proxy_ip, proxy_port = act_kwargs.cluster["temp_cluster_proxy"].split(":")
            act_kwargs.cluster["proxy_ip"] = proxy_ip
            act_kwargs.cluster["proxy_port"] = int(proxy_port)

            act_kwargs.exec_ip = act_kwargs.cluster["proxy_ip"]
            act_kwargs.get_redis_payload_func = RedisActPayload.proxy_shutdown_payload.__name__
            redis_pipeline.add_act(
                act_name=_("{}下架proxy实例").format(act_kwargs.cluster["proxy_ip"]),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
        # #### 下架旧实例完成 #############################################################################
        act_kwargs.cluster = {
            "related_rollback_bill_id": info["related_rollback_bill_id"],
            "bk_biz_id": ticket_bk_biz_id,
            "prod_cluster": info["prod_cluster"],
            "meta_func_name": RedisDBMeta.update_rollback_task_status.__name__,
            "cluster_type": act_kwargs.cluster["cluster_type"],
            "destroyed_status": DestroyedStatus.DESTROYED,
        }
        redis_pipeline.add_act(
            act_name=_("更新构造记录为已销毁"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        return redis_pipeline.build_sub_process(sub_name=_("集群[{}]数据构造销毁").format(info["prod_cluster"]))
