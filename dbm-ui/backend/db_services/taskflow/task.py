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
import itertools
import logging
from datetime import datetime, timedelta
from typing import Any, Union

from bamboo_engine.api import EngineAPIResult
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.eri.models import (
    CallbackData,
    ContextOutputs,
    ContextValue,
    Data,
    ExecutionData,
    ExecutionHistory,
    Node,
    Process,
    Schedule,
    State,
)
from pipeline.eri.signals import post_set_state

from backend.db_meta.exceptions import ClusterExclusiveOperateException
from backend.db_meta.models import Cluster
from backend.db_meta.models.sqlserver_dts import SqlserverDtsInfo
from backend.db_services.taskflow.constants import MAX_AUTO_RETRY_TIMES, RETRY_INTERVAL
from backend.db_services.taskflow.exceptions import RetryNodeException
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.constants import FlowRetryType, TicketType
from backend.ticket.models import Flow, Ticket

logger = logging.getLogger("flow")


@shared_task
def retry_node(root_id: str, flow_node: FlowNode, retry_times: int) -> Union[EngineAPIResult, Any]:
    """重试flow任务节点"""

    def send_flow_state(state, _root_id, _node_id, _version_id):
        post_set_state.send(
            sender=None,
            node_id=flow_node.node_id,
            to_state=state,
            version=flow_node.version_id,
            root_id=flow_node.root_id,
            parent_id=None,
            loop=None,
        )

    # 实例化一个Service实例用于捕获日志到日志平台
    service = BaseService()
    service.setup_runtime_attrs(root_pipeline_id=root_id, id=flow_node.node_id, version=flow_node.version_id)

    # 限制最大重试次数
    if retry_times > MAX_AUTO_RETRY_TIMES:
        error_msg = _("自动重试次数已超过最大重试次数{}, 请重新手动重试").format(MAX_AUTO_RETRY_TIMES)
        service.log_error(error_msg)
        send_flow_state(StateType.FAILED, root_id, flow_node.node_id, flow_node.version_id)
        return EngineAPIResult(result=False, message=error_msg)

    # 判断重试任务关联单据是否存在执行互斥
    try:
        ticket = Ticket.objects.get(id=flow_node.uid)
        ticket_type = ticket.ticket_type
        if ticket_type == TicketType.SQLSERVER_DISABLE.value or ticket_type in [
            TicketType.SQLSERVER_INCR_MIGRATE,
            TicketType.SQLSERVER_FULL_MIGRATE,
        ]:
            # 判断sqlserver禁用、迁移集群跟迁移记录是否互斥
            SqlserverDtsInfo.dts_info_clusive(ticket_id=ticket.id, ticket_type=ticket_type, details=ticket.details)
        cluster_ids = fetch_cluster_ids(ticket.details)
        Cluster.handle_exclusive_operations(cluster_ids, ticket.ticket_type, exclude_ticket_ids=[ticket.id])
    except ClusterExclusiveOperateException as e:
        # 互斥下: 手动重试直接报错，自动重试则延迟一定时间后重新执行该任务
        service.log_info(_("存在执行互斥，正在进行重试，当前重试次数为{}").format(retry_times))
        flow = Flow.objects.get(flow_obj_id=flow_node.root_id)
        if flow.retry_type == FlowRetryType.MANUAL_RETRY:
            raise RetryNodeException(_("执行互斥错误信息: {}").format(e))
        else:
            # 认为重试中也是RUNNING状态
            if retry_times == 1:
                send_flow_state(StateType.RUNNING, root_id, flow_node.node_id, flow_node.version_id)

            retry_node.apply_async((root_id, flow_node, retry_times + 1), countdown=RETRY_INTERVAL)
            return EngineAPIResult(result=False, message=_("存在执行互斥将自动进行重试..."))
    except (Ticket.DoesNotExist, ValueError):
        # 如果单据不存在，则忽略校验
        pass

    # 进行重试操作
    result = BambooEngine(root_id=root_id).retry_node(node_id=flow_node.node_id)
    if not result.result:
        raise RetryNodeException(str(result.exc.args))

    service.log_info(_("重试成功"))
    return result


def clean_bamboo_engine_expired_data():
    """定时清理流程引擎的过期任务"""

    def get_clean_pipeline_instance_data(pipeline_ids):
        """
        根据 pipeline_instance_id 列表清除对应任务执行数据
        :param pipeline_ids: 需要清理的 pipeline_instance_id 列表
        :return: Dict[str, QuerySet]
        """
        # dbm的流程树和流程节点
        flow_trees = FlowTree.objects.filter(root_id__in=pipeline_ids)
        flow_nodes = FlowNode.objects.filter(root_id__in=pipeline_ids)

        # bamboo流程相关数据
        context_value = ContextValue.objects.filter(pipeline_id__in=pipeline_ids)
        context_outputs = ContextOutputs.objects.filter(pipeline_id__in=pipeline_ids)
        process = Process.objects.filter(root_pipeline_id__in=pipeline_ids)
        states = State.objects.filter(root_id__in=pipeline_ids)

        # bamboo流程节点相关数据
        node_ids = [BambooEngine(pipeline_id).get_pipeline_tree_nodes() for pipeline_id in pipeline_ids]
        node_ids = list(itertools.chain(*node_ids))
        nodes = Node.objects.filter(node_id__in=node_ids)
        data = Data.objects.filter(node_id__in=node_ids)
        execution_history = ExecutionHistory.objects.filter(node_id__in=node_ids)
        execution_data = ExecutionData.objects.filter(node_id__in=node_ids)
        callback_data = CallbackData.objects.filter(node_id__in=node_ids)
        schedules = Schedule.objects.filter(node_id__in=node_ids)

        return {
            "context_value": context_value,
            "context_outputs": context_outputs,
            "process": process,
            "node": nodes,
            "data": data,
            "state": states,
            "execution_history": execution_history,
            "execution_data": execution_data,
            "callback_data": callback_data,
            "schedules": schedules,
            "flow_nodes": flow_nodes,
            "flow_trees": flow_trees,
        }

    if not settings.ENABLE_CLEAN_EXPIRED_BAMBOO_TASK:
        logger.info(_("未开启bamboo数据清理，跳过..."))
        return

    expire_time = datetime.now() - timedelta(days=settings.BAMBOO_TASK_VALIDITY_DAY)
    one_batch_num = settings.BAMBOO_TASK_EXPIRE_ONE_BATCH_NUM

    logger.info(_("开始清理时间{}前的bamboo数据").format(expire_time))

    try:
        tree_qs = FlowTree.objects.filter(created_at__lt=expire_time, is_expired=False).order_by("created_at")
        root_ids = list(tree_qs.values_list("root_id", flat=True)[:one_batch_num])
        if not root_ids:
            logger.info(_("没有需要清理的bamboo数据，跳过..."))

        data_to_clean = get_clean_pipeline_instance_data(list(root_ids))
        # 按model清理bamboo数据，如果开启了flow实例清理，则删除流程树和流程节点。否则仅标记为expire
        with transaction.atomic():
            for field, qs in data_to_clean.items():
                logger.info(_("{}数据清理...").format(field))
                if field not in ["flow_nodes", "flow_trees"] or settings.ENABLE_CLEAN_EXPIRED_FLOW_INSTANCE:
                    qs.delete()
                else:
                    qs.update(is_expired=True)
        logger.info(_("bamboo数据清理成功").format(expire_time))
    except Exception as e:
        logger.exception(_("bamboo数据清理失败，错误原因: {}").format(e))
