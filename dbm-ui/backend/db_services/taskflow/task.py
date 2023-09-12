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
from typing import Any, Union

from bamboo_engine.api import EngineAPIResult
from celery import shared_task
from django.utils.translation import ugettext as _
from pipeline.eri.signals import post_set_state

from backend.db_meta.exceptions import ClusterExclusiveOperateException
from backend.db_meta.models import Cluster
from backend.db_services.taskflow.constants import MAX_AUTO_RETRY_TIMES, RETRY_INTERVAL
from backend.db_services.taskflow.exceptions import RetryNodeException
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import FlowRetryType
from backend.ticket.models import Flow, Ticket
from backend.utils.basic import get_target_items_from_details

logger = logging.getLogger("flow")


@shared_task
def retry_node(root_id: str, node_id: str, retry_times: int) -> Union[EngineAPIResult, Any]:
    """重试flow任务节点"""

    def send_flow_state(state, _root_id, _node_id, _version_id):
        post_set_state.send(
            sender=None,
            node_id=node_id,
            to_state=state,
            version=flow_node.version_id,
            root_id=flow_node.root_id,
            parent_id=None,
            loop=None,
        )

    flow_node = FlowNode.objects.get(root_id=root_id, node_id=node_id)

    # 实例化一个Service实例用于捕获日志到日志平台
    service = BaseService()
    service.setup_runtime_attrs(root_pipeline_id=root_id, id=node_id, version=flow_node.version_id)
    service.log_info(_("存在执行互斥，正在进行重试，当前重试次数为{}").format(retry_times))

    # 限制最大重试次数
    if retry_times > MAX_AUTO_RETRY_TIMES:
        error_msg = _("自动重试次数已超过最大重试次数{}, 请重新手动重试").format(MAX_AUTO_RETRY_TIMES)
        service.log_error(error_msg)
        send_flow_state(StateType.FAILED, root_id, flow_node.node_id, flow_node.version_id)
        return EngineAPIResult(result=False, message=error_msg)

    # 判断重试任务关联单据是否存在执行互斥
    try:
        ticket = Ticket.objects.get(id=flow_node.uid)
        cluster_ids = get_target_items_from_details(ticket.details, match_keys=["cluster_id", "cluster_ids"])
        Cluster.handle_exclusive_operations(cluster_ids, ticket.ticket_type)
    except ClusterExclusiveOperateException as e:
        # 互斥下: 手动重试直接报错，自动重试则延迟一定时间后重新执行该任务
        flow = Flow.objects.get(flow_obj_id=flow_node.root_id)
        if flow.retry_type == FlowRetryType.MANUAL_RETRY:
            raise RetryNodeException(_("执行互斥错误信息: {}").format(e))
        else:
            # 认为重试中也是RUNNING状态
            if retry_times == 1:
                send_flow_state(StateType.RUNNING, root_id, flow_node.node_id, flow_node.version_id)

            retry_node.apply_async((root_id, node_id, retry_times + 1), countdown=RETRY_INTERVAL)
            return EngineAPIResult(result=False, message=_("存在执行互斥将自动进行重试..."))
    except (Ticket.DoesNotExist, ValueError):
        # 如果单据不存在，则忽略校验
        pass

    # 进行重试操作
    result = BambooEngine(root_id=root_id).retry_node(node_id=node_id)
    if not result.result:
        raise RetryNodeException(str(result.exc.args))

    service.log_info(_("重试成功"))
    return result
