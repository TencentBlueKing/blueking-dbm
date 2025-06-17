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

from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.io import ObjectItemSchema, StringItemSchema

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord, Flow, Ticket
from backend.ticket.todos.pipeline_todo import PipelineTodo

logger = logging.getLogger("root")


# 单次回调机制，等待外部调用确认是否继续
class PauseWithTicketLockCheckService(BaseService):
    """
    暂停节点V2版本，需人工出发继续执行
    同时确认后会重新判断单据是否可以互斥，如果不互斥则回滚暂停之前状态，同时报异常
    重试再确认执行的逻辑
    """

    __need_schedule__ = True

    def _execute(self, data, parent_data):
        self.log_info("execute PauseWithTicketLockCheckService")
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 获取单据和flow信息
        ticket_id = global_data["uid"]
        ticket = Ticket.objects.get(id=ticket_id)
        flow = Flow.objects.get(ticket=ticket, flow_obj_id=global_data["job_root_id"])

        # 相关记录修改状态
        for cluster_id in kwargs["cluster_ids"]:
            record = ClusterOperateRecord.objects.get(
                cluster_id=cluster_id,
                ticket=ticket,
                flow=flow,
            )
            record.update_is_pause_with_pause()

        # 创建一条代办
        PipelineTodo.create(ticket, flow, self.runtime_attrs.get("root_pipeline_id"), self.runtime_attrs.get("id"))

        self.log_info("pause kwargs: {}".format(kwargs))
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        check_result = True
        if callback_data is not None:
            self.log_info("callback_data: {}".format(callback_data))
            data.outputs.callback_data = callback_data

            # 判断是否可以继续执行
            kwargs = data.get_one_of_inputs("kwargs")
            if kwargs.get("cluster_ids"):
                global_data = data.get_one_of_inputs("global_data")
                ticket_id = global_data["uid"]
                ticket = Ticket.objects.get(id=ticket_id)
                flow = Flow.objects.get(ticket=ticket, flow_obj_id=global_data["job_root_id"])
                check_result = self._has_active_exec(
                    kwargs.get("cluster_ids"), ticket, flow, kwargs["release_unlock_ticket_type_list"]
                )

            self.finish_schedule()
        return check_result

    @transaction.atomic
    def _has_active_exec(self, cluster_ids, ticket, flow, release_unlock_ticket_type_list):
        """
        判断当前节点的互斥关系，是否可以执行
        """
        self.log_info(_("判断流程是否可以继续执行..."))
        check_result = True
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            record = ClusterOperateRecord.objects.select_for_update().get(
                cluster_id=cluster_id,
                ticket=ticket,
                flow=flow,
            )
            # 判断是否提前释放单据互斥锁
            record.remove_unlock_ticket_type_config_operations(release_unlock_ticket_type_list)
            for ticket_type in release_unlock_ticket_type_list:
                self.log_info(
                    _(
                        "集群[{}]  释放解除单据互斥锁关系，以下单据类型重新互斥 :[{}]\n".format(
                            cluster.immute_domain, TicketType.get_choice_label(ticket_type)
                        )
                    )
                )
            # 判断是否能能执行
            is_pass, exclusive_infos = record.has_exclusive_operations_pause()
            if is_pass:
                # 表示没有互斥，跳过
                continue
            # 互斥打印互斥信息
            for info in exclusive_infos:
                self.log_error(_("当前操作的集群(id:{})的操作「{}」存在执行互斥".format(cluster_id, info["exclusive_ticket"])))
            check_result = False

        # 判断互斥结果，如果互斥结果不通过，则回滚暂停前的配置
        if not check_result:
            transaction.set_rollback(True)

        return check_result

    def inputs_format(self):
        return [
            self.InputItem(
                name=_("描述"), key="description", type="string", schema=StringItemSchema(description="description")
            )
        ]

    def outputs_format(self):
        return [
            self.OutputItem(
                name=_("回调数据"),
                key="callback_data",
                type="object",
                schema=ObjectItemSchema(description="node_callback api with params(dict)", property_schemas={}),
            )
        ]


class PauseWithTicketLockCheckComponent(Component):
    name = _("暂停,确认执行后继续判断互斥条件")
    code = "pause_with_ticket_lock_check"
    bound_service = PauseWithTicketLockCheckService
