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
import datetime
import json
import traceback
import uuid
from typing import List

from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.db_services.redis.redis_dts.models import TendisplusLightningJob, TendisplusLightningTask
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, TendisplusLightningContext
from backend.flow.utils.redis.redis_proxy_util import get_cluster_info_by_cluster_id, lightning_cluster_nodes


class TendisplusClusterLightningService(BaseService):
    """
    tendisplus集群迁移
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(30)

    def _execute(self, data, parent_data):
        kwargs: ActKwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data: TendisplusLightningContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        if trans_data.ticket_id and trans_data.dst_cluster:
            """如果 ticket_id 和 dst_cluster 已经存在,则表示已经执行过了,无需重复插入"""
            return True
        try:
            ticket_id = int(global_data["uid"])
            bk_biz_id = int(global_data["bk_biz_id"])
            cluster_id = int(kwargs["cluster"]["cluster_id"])
            cos_file_keys = kwargs["cluster"]["cos_file_keys"]
            cluster_info = get_cluster_info_by_cluster_id(cluster_id)
            cluster_nodes_data = lightning_cluster_nodes(cluster_id=cluster_id)
            with transaction.atomic():
                job = TendisplusLightningJob()
                job.ticket_id = ticket_id
                job.user = global_data["created_by"]
                job.bk_biz_id = str(bk_biz_id)
                job.bk_cloud_id = cluster_info["bk_cloud_id"]
                job.dst_cluster = cluster_info["immute_domain"] + ":" + str(cluster_info["proxy_port"])
                job.dst_cluster_id = cluster_id
                job.cluster_nodes = json.dumps(cluster_nodes_data)
                job.create_time = datetime.datetime.now()
                job.save()

                for cos_file_key in cos_file_keys:
                    task = TendisplusLightningTask()
                    task.task_id = uuid.uuid1().hex
                    task.ticket_id = job.ticket_id
                    task.user = job.user
                    task.bk_biz_id = job.bk_biz_id
                    task.bk_cloud_id = cluster_info["bk_cloud_id"]
                    task.cos_key = cos_file_key
                    task.cos_file_size = 0
                    task.dts_server = "1.1.1.1"
                    task.dst_cluster = job.dst_cluster
                    task.dst_cluster_id = job.dst_cluster_id
                    task.dst_cluster_priority = 1
                    task.dst_zonename = cluster_info["cluster_city_name"]
                    task.task_type = ""
                    task.status = 0
                    task.create_time = datetime.datetime.now()
                    task.update_time = datetime.datetime.now()
                    task.save()

        except Exception as e:
            traceback.print_exc()
            self.log_error("tendisplus lightning failed:{}".format(e))
            return False
        self.log_info("tendisplus lightning success")
        trans_data.ticket_id = ticket_id
        trans_data.dst_cluster = cluster_info["immute_domain"] + ":" + str(cluster_info["proxy_port"])
        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data: TendisplusLightningContext = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        ticket_id = trans_data.ticket_id
        dst_cluster = trans_data.dst_cluster
        tasks_fows = TendisplusLightningTask.objects.filter(ticket_id=ticket_id, dst_cluster=dst_cluster)
        if self.__is_any_task_fail(tasks_fows):
            self.log_info(_("ticket_id:{} dst_cluster:{} 有任务失败").format(ticket_id, dst_cluster))
            self.finish_schedule()
            return False
        if self.__is_any_task_running(tasks_fows):
            self.log_info(_("ticket_id:{} dst_cluster:{} 有任务仍然在运行中").format(ticket_id, dst_cluster))
            return True
        # 任务全部都成功了
        self.log_info(_("ticket_id:{} dst_cluster:{} 全部任务执行成功").format(ticket_id, dst_cluster))
        self.finish_schedule()
        return True

    def __is_any_task_fail(self, tasks: List[TendisplusLightningTask]) -> bool:
        """
        判断是否还有任务失败
        """
        for task in tasks:
            if task.status == -1:
                return True

    def __is_any_task_running(self, tasks: List[TendisplusLightningTask]) -> bool:
        """
        判断是否还有任务运行中
        """
        for task in tasks:
            if task.status in [0, 1]:
                return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class TendisplusClusterLightningComponent(Component):
    name = __name__
    code = "tendisplus_cluster_lightning"
    bound_service = TendisplusClusterLightningService
