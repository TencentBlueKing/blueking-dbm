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


import ast
import logging.config
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.flow.consts import DBActuatorTypeEnum, DnsOpType, RedisActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import RedisBatchShutdownAtomJob
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
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

        task = TbTendisRollbackTasks.objects.filter(
            related_rollback_bill_id=related_rollback_bill_id, bk_biz_id=bk_biz_id, prod_cluster=prod_cluster
        ).order_by("-update_at")
        task_list = list(task.values())
        # 这里需要加吗
        # if len(task_list) != 1:
        #     raise Exception(
        #         "单据{},构造源集群{},返回{}条记录不唯一，请检查！！！".format(related_rollback_bill_id, prod_cluster, len(task_list))
        #     )
        formatted_tasks = []
        for task in task_list:
            formatted_task = {}
            for key, value in task.items():
                if isinstance(value, datetime):
                    formatted_task[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    formatted_task[key] = value
            formatted_tasks.append(formatted_task)
        return dict(formatted_tasks[0])

    def redis_rollback_task_delete_flow(self):
        """
        1、删除包含删除redis 实例的cmdb，下掉redis实例，下掉proxy实例，最后再更新构造记录为已销毁
        构造记录销毁需要元数据：
         1、master ip_ports 下架，元数据处理
         2、proxy下架
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        sub_pipelines = []
        for info in self.data["infos"]:

            tasks_info = self.__get_cluster_info(
                self.data["bk_biz_id"], info["related_rollback_bill_id"], info["prod_cluster"]
            )

            logger.info("redis_rollback_task_delete_flow tasks_info:{}".format(tasks_info))
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.is_update_trans_data = True
            act_kwargs.cluster = {
                **tasks_info,
                "operate": self.data["ticket_type"],
            }
            # 初始化
            act_kwargs.cluster["cluster_type"] = act_kwargs.cluster["temp_cluster_type"]
            redis_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            master_ports = {}
            for instance in ast.literal_eval(act_kwargs.cluster["temp_instance_range"]):
                ip, port = instance.split(":")
                if ip in master_ports:
                    master_ports[ip].append(int(port))
                else:
                    master_ports[ip] = [int(port)]
            act_kwargs.cluster["master_ports"] = master_ports

            # #### 下架旧redis实例 #############################################################################
            sub_pipelines = []
            for ip_address, ports in master_ports.items():
                params = {
                    "ip": ip_address,
                    "ports": ports,
                }
                sub_builder = RedisBatchShutdownAtomJob(self.root_id, self.data, act_kwargs, params)
                sub_pipelines.append(sub_builder)
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

            # #### 下架旧proxy实例 #############################################################################
            # 重新赋值，因为下架redis时cluster会被赋值
            # act_kwargs.cluster = {**tasks_info}
            act_kwargs.cluster["cluster_type"] = act_kwargs.cluster["temp_cluster_type"]

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
            # 更新构造记录为已销毁
            act_kwargs.cluster = {
                "related_rollback_bill_id": info["related_rollback_bill_id"],
                "bk_biz_id": self.data["bk_biz_id"],
                "prod_cluster": info["prod_cluster"],
                "meta_func_name": RedisDBMeta.update_rollback_task_status.__name__,
                "cluster_type": act_kwargs.cluster["cluster_type"],
            }
            redis_pipeline.add_act(
                act_name=_("删除构造记录元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
            )

        redis_pipeline.run_pipeline()
