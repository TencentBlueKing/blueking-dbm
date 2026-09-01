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

from django.core.cache import cache
from django.db.models import Q
from django.utils.translation import gettext as _
from pipeline.eri.models import Schedule

from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import CHILD2RUNNER_CACHE_PREFIX
from backend.flow.signal.callback_map import create_ticket_handler
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")

TERMINAL_STATES = {StateType.FINISHED, StateType.FAILED, StateType.REVOKED}


def _resolve_parent_root_id(ticket_id: int):
    parent_tree = (
        FlowTree.objects.filter(uid=ticket_id, ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE)
        .order_by("-created_at")
        .first()
    )
    if not parent_tree:
        return None
    return parent_tree.root_id


def _resolve_runner_node_id(parent_root_id: str, child_root_id: str):
    candidate_node_ids = list(
        FlowNode.objects.filter(
            root_id=parent_root_id, status__in=[StateType.RUNNING, StateType.CREATED, StateType.READY]
        )
        .order_by("-updated_at")
        .values_list("node_id", flat=True)[:20]
    )
    if not candidate_node_ids:
        return None

    engine = BambooEngine(root_id=parent_root_id)
    for node_id in candidate_node_ids:
        try:
            node_outputs = engine.get_node_output_data(node_id).data or {}
            if node_outputs.get("child_root_id") == child_root_id:
                return node_id
        except Exception as e:
            logger.warning(
                _("Resolve runner node output failed. parent_root_id={}, node_id={}, err={}").format(
                    parent_root_id, node_id, e
                )
            )

    return None


def wakeup_redis_rollback_runner_by_child(child_root_id: str, child_state: str, trigger: str) -> int:
    """
    Wake up parent FlowRunner nodes bound to a child pipeline.

    This is best-effort and safe to call repeatedly.
    """
    logger.info(
        f"Wakeup redis rollback runner by child. "
        f"child_root_id={child_root_id}, child_state={child_state}, trigger={trigger}"
    )

    cached_key = f"{CHILD2RUNNER_CACHE_PREFIX}:{child_root_id}"
    cached = cache.get(cached_key)
    if cached:
        parent_root_id = cached["parent_root_id"]
        runner_node_id = cached["runner_node_id"]
    else:
        # Fallback path, normally should not get here, there's no index covering the obj_id fields.
        report = Report.objects.filter(
            Q(rollback_flow_obj_id=child_root_id) | Q(delete_flow_obj_id=child_root_id)
        ).first()
        if not report or not report.ticket_id:
            logger.warning(_("No matching report for child_root_id={}").format(child_root_id))
            return 0

        parent_root_id = _resolve_parent_root_id(ticket_id=report.ticket_id)
        if not parent_root_id:
            logger.warning(
                _("Resolve parent root id failed for report {} ticket_id={}").format(report.id, report.ticket_id)
            )
            return 0

        runner_node_id = _resolve_runner_node_id(parent_root_id=parent_root_id, child_root_id=child_root_id)
        if not runner_node_id:
            logger.warning(
                _("Resolve runner node id failed. parent_root_id={}, child_root_id={}").format(
                    parent_root_id, child_root_id
                )
            )
            return 0

    logger.info(
        f"Resolved runner mapping. parent_root_id={parent_root_id}, "
        f"runner_node_id={runner_node_id}, cached={'yes' if cached else 'no'}"
    )

    # Preserve guard: only wake runners that are still active. After a runner records
    # SCENE_PRESERVED it finishes normally and the separate confirmation node is DBA-driven.
    runner_alive = FlowNode.objects.filter(
        root_id=parent_root_id,
        node_id=runner_node_id,
        status__in=[StateType.RUNNING, StateType.CREATED, StateType.READY],
    ).exists()
    if not runner_alive:
        if cached:
            cache.delete(cached_key)  # drop stale cache so we do not retry a dead wakeup
        logger.warning(
            _(
                "Redis rollback runner node is not active, skip wakeup. parent_root_id={}, "
                "runner_node_id={}, child_root_id={}"
            ).format(parent_root_id, runner_node_id, child_root_id)
        )
        return 0

    try:
        Schedule.objects.filter(node_id=runner_node_id, scheduling=True, finished=False).update(scheduling=False)

        callback_result = BambooEngine(root_id=parent_root_id).callback(
            node_id=runner_node_id,
            desc={"child_root_id": child_root_id, "child_state": child_state, "trigger": trigger},
        )
        if callback_result.result:
            cache.delete(cached_key)
            return 1
        logger.warning(
            _("Redis rollback runner callback failed. parent_root_id={}, runner_node_id={}, child_root_id={}").format(
                parent_root_id, runner_node_id, child_root_id
            )
        )
    except Exception as e:
        logger.warning(
            _(
                "Redis rollback runner callback exception. parent_root_id={}, runner_node_id={}, child_root_id={}, err={}"
            ).format(parent_root_id, runner_node_id, child_root_id, e)
        )

    return 0


def _handle_redis_sub_ticket_callback(root_id: str, status: str, ticket_id: int):
    if status not in TERMINAL_STATES:
        return

    if not ticket_id:
        return

    ticket = Ticket.objects.filter(id=ticket_id).only("ticket_type").first()
    if not ticket:
        logger.info(_("Redis rollback drill sub-ticket callback ticket not found, ticket_id={}").format(ticket_id))
        return

    if ticket.ticket_type != TicketType.REDIS_ROLLBACK_EXERCISE:
        return

    # `status` is the node-level state (fires for every node), not the pipeline state.
    # Only wake up the runner when the pipeline itself reaches a terminal state.
    try:
        tree = FlowTree.objects.get(root_id=root_id)
    except FlowTree.DoesNotExist:
        logger.warning(_("Redis rollback drill sub-ticket callback tree not found, root_id={}").format(root_id))
        return

    if tree.status not in TERMINAL_STATES:
        return

    wakeup_redis_rollback_runner_by_child(child_root_id=root_id, child_state=tree.status, trigger="post_set_state")


@create_ticket_handler(TicketType.REDIS_DATA_STRUCTURE)
def redis_data_structure_callback_handler(root_id: str, node_id: str, status: StateType, ticket_id: int, **kwargs):
    _handle_redis_sub_ticket_callback(root_id=root_id, status=status, ticket_id=ticket_id)


@create_ticket_handler(TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE)
def redis_data_structure_task_delete_callback_handler(
    root_id: str, node_id: str, status: StateType, ticket_id: int, **kwargs
):
    _handle_redis_sub_ticket_callback(root_id=root_id, status=status, ticket_id=ticket_id)
