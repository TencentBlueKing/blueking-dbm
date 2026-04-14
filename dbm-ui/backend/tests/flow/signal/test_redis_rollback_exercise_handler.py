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
from unittest.mock import MagicMock, patch

import pytest
from bamboo_engine.api import EngineAPIResult

from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.flow.consts import StateType
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import CHILD2RUNNER_CACHE_PREFIX
from backend.flow.signal.callback_map import TICKET_TYPE_HANDLERS
from backend.flow.signal.redis_rollback_exercise_handler import (
    _resolve_runner_node_id,
    redis_data_structure_callback_handler,
    redis_data_structure_task_delete_callback_handler,
    wakeup_redis_rollback_runner_by_child,
)
from backend.ticket.constants import TicketType

pytestmark = pytest.mark.django_db


# ==================== wakeup: cache hit path ====================


@patch("backend.flow.signal.redis_rollback_exercise_handler.cache.get")
@patch("backend.flow.signal.redis_rollback_exercise_handler.Schedule.objects.filter")
@patch(
    "backend.flow.signal.redis_rollback_exercise_handler.BambooEngine.callback",
    return_value=EngineAPIResult(result=True, data={}, message=""),
)
def test_wakeup_cache_hit_skips_report_query(mock_callback, mock_schedule_filter, mock_cache_get):
    mock_cache_get.return_value = {"parent_root_id": "parent_root_id", "runner_node_id": "runner_node_id"}
    mock_schedule_filter.return_value.update = MagicMock(return_value=1)

    result = wakeup_redis_rollback_runner_by_child("child_root_id", StateType.FINISHED, "unit_test")

    assert result == 1
    mock_cache_get.assert_called_once_with(f"{CHILD2RUNNER_CACHE_PREFIX}:child_root_id")
    mock_schedule_filter.assert_called_once_with(node_id="runner_node_id", scheduling=True, finished=False)
    mock_schedule_filter.return_value.update.assert_called_once_with(scheduling=False)
    mock_callback.assert_called_once_with(
        node_id="runner_node_id",
        desc={"child_root_id": "child_root_id", "child_state": StateType.FINISHED, "trigger": "unit_test"},
    )


@patch("backend.flow.signal.redis_rollback_exercise_handler.cache.get")
@patch("backend.flow.signal.redis_rollback_exercise_handler.Schedule.objects.filter")
@patch(
    "backend.flow.signal.redis_rollback_exercise_handler.BambooEngine.callback",
    return_value=EngineAPIResult(result=False, data={}, message="callback rejected"),
)
def test_wakeup_cache_hit_callback_fails_returns_0(mock_callback, mock_schedule_filter, mock_cache_get):
    """When the callback itself returns result=False, wakeup should return 0."""
    mock_cache_get.return_value = {"parent_root_id": "parent_root_id", "runner_node_id": "runner_node_id"}
    mock_schedule_filter.return_value.update = MagicMock(return_value=1)

    result = wakeup_redis_rollback_runner_by_child("child_root_id", StateType.FINISHED, "unit_test")

    assert result == 0
    mock_callback.assert_called_once()


@patch("backend.flow.signal.redis_rollback_exercise_handler.cache.get")
@patch("backend.flow.signal.redis_rollback_exercise_handler.Schedule.objects.filter")
@patch(
    "backend.flow.signal.redis_rollback_exercise_handler.BambooEngine.callback",
    side_effect=Exception("callback boom"),
)
def test_wakeup_cache_hit_callback_exception_returns_0(mock_callback, mock_schedule_filter, mock_cache_get):
    """When the callback raises an exception, wakeup should catch it and return 0."""
    mock_cache_get.return_value = {"parent_root_id": "parent_root_id", "runner_node_id": "runner_node_id"}
    mock_schedule_filter.return_value.update = MagicMock(return_value=1)

    result = wakeup_redis_rollback_runner_by_child("child_root_id", StateType.FINISHED, "unit_test")

    assert result == 0


# ==================== wakeup: cache miss fallback path ====================


@patch("backend.flow.signal.redis_rollback_exercise_handler.cache.get", return_value=None)
@patch("backend.flow.signal.redis_rollback_exercise_handler._resolve_parent_root_id", return_value="parent_root_id")
@patch("backend.flow.signal.redis_rollback_exercise_handler._resolve_runner_node_id", return_value="runner_node_id")
@patch("backend.flow.signal.redis_rollback_exercise_handler.Schedule.objects.filter")
@patch(
    "backend.flow.signal.redis_rollback_exercise_handler.BambooEngine.callback",
    return_value=EngineAPIResult(result=True, data={}, message=""),
)
def test_wakeup_cache_miss_falls_back_to_report(
    mock_callback, mock_schedule_filter, _mock_resolve_runner, _mock_resolve_parent, _mock_cache_get
):
    report = Report.objects.create(
        cluster_id=1,
        cluster_domain="d",
        cluster_type="Redis",
        instance_ip="127.0.0.1",
        instance_port=6379,
        redis_version="7.0",
        ticket_id=1,
        rollback_flow_obj_id="child_root_id",
    )

    mock_schedule_filter.return_value.update = MagicMock(return_value=1)
    result = wakeup_redis_rollback_runner_by_child("child_root_id", StateType.FINISHED, "unit_test")

    assert result == 1
    mock_callback.assert_called_once()
    report.delete()


@patch("backend.flow.signal.redis_rollback_exercise_handler.cache.get", return_value=None)
def test_wakeup_cache_miss_no_report_returns_0(_mock_cache_get):
    """When cache misses and no report matches, wakeup should return 0."""
    result = wakeup_redis_rollback_runner_by_child("orphan_child_root_id", StateType.FINISHED, "unit_test")
    assert result == 0


@patch("backend.flow.signal.redis_rollback_exercise_handler.cache.get", return_value=None)
@patch("backend.flow.signal.redis_rollback_exercise_handler._resolve_parent_root_id", return_value=None)
def test_wakeup_cache_miss_no_parent_root_id_returns_0(_mock_resolve_parent, _mock_cache_get):
    """When parent_root_id cannot be resolved, wakeup should return 0."""
    report = Report.objects.create(
        cluster_id=1,
        cluster_domain="d",
        cluster_type="Redis",
        instance_ip="127.0.0.1",
        instance_port=6379,
        redis_version="7.0",
        ticket_id=1,
        rollback_flow_obj_id="child_root_id",
    )

    result = wakeup_redis_rollback_runner_by_child("child_root_id", StateType.FINISHED, "unit_test")

    assert result == 0
    report.delete()


@patch("backend.flow.signal.redis_rollback_exercise_handler.cache.get", return_value=None)
@patch("backend.flow.signal.redis_rollback_exercise_handler._resolve_parent_root_id", return_value="parent_root_id")
@patch("backend.flow.signal.redis_rollback_exercise_handler._resolve_runner_node_id", return_value=None)
def test_wakeup_cache_miss_no_runner_node_id_returns_0(_mock_resolve_runner, _mock_resolve_parent, _mock_cache_get):
    """When runner_node_id cannot be resolved, wakeup should return 0."""
    report = Report.objects.create(
        cluster_id=1,
        cluster_domain="d",
        cluster_type="Redis",
        instance_ip="127.0.0.1",
        instance_port=6379,
        redis_version="7.0",
        ticket_id=1,
        rollback_flow_obj_id="child_root_id",
    )

    result = wakeup_redis_rollback_runner_by_child("child_root_id", StateType.FINISHED, "unit_test")

    assert result == 0
    report.delete()


@patch("backend.flow.signal.redis_rollback_exercise_handler.cache.get", return_value=None)
def test_wakeup_cache_miss_report_without_ticket_id_returns_0(_mock_cache_get):
    """When the matching report has ticket_id=0 (falsy), wakeup should return 0."""
    report = Report.objects.create(
        cluster_id=1,
        cluster_domain="d",
        cluster_type="Redis",
        instance_ip="127.0.0.1",
        instance_port=6379,
        redis_version="7.0",
        ticket_id=0,
        rollback_flow_obj_id="child_root_id",
    )

    result = wakeup_redis_rollback_runner_by_child("child_root_id", StateType.FINISHED, "unit_test")

    assert result == 0
    report.delete()


# ==================== handler registration ====================


def test_redis_sub_ticket_handlers_registered():
    assert TICKET_TYPE_HANDLERS.get(TicketType.REDIS_DATA_STRUCTURE.lower()) == redis_data_structure_callback_handler
    assert (
        TICKET_TYPE_HANDLERS.get(TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE.lower())
        == redis_data_structure_task_delete_callback_handler
    )


# ==================== _handle_redis_sub_ticket_callback ====================


@patch("backend.flow.signal.redis_rollback_exercise_handler.FlowTree.objects.get")
@patch("backend.flow.signal.redis_rollback_exercise_handler.Ticket.objects.filter")
@patch("backend.flow.signal.redis_rollback_exercise_handler.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_terminal_state_with_drill_ticket(mock_wakeup, mock_ticket_filter, mock_flowtree_get):
    mock_ticket_filter.return_value.only.return_value.first.return_value = MagicMock(
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE
    )
    mock_flowtree_get.return_value = MagicMock(status=StateType.FINISHED)
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id="child_root_id",
        status=StateType.FINISHED,
        ticket_id=1,
    )
    mock_wakeup.assert_called_once_with(
        child_root_id="child_root_id", child_state=StateType.FINISHED, trigger="post_set_state"
    )


@pytest.mark.parametrize("terminal_state", [StateType.FAILED, StateType.REVOKED])
@patch("backend.flow.signal.redis_rollback_exercise_handler.FlowTree.objects.get")
@patch("backend.flow.signal.redis_rollback_exercise_handler.Ticket.objects.filter")
@patch("backend.flow.signal.redis_rollback_exercise_handler.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_failed_and_revoked_also_trigger_wakeup(
    mock_wakeup, mock_ticket_filter, mock_flowtree_get, terminal_state
):
    """FAILED and REVOKED are also terminal states that should trigger wakeup."""
    mock_ticket_filter.return_value.only.return_value.first.return_value = MagicMock(
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE
    )
    mock_flowtree_get.return_value = MagicMock(status=terminal_state)
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id="child_root_id",
        status=terminal_state,
        ticket_id=1,
    )
    mock_wakeup.assert_called_once_with(
        child_root_id="child_root_id", child_state=terminal_state, trigger="post_set_state"
    )


@patch("backend.flow.signal.redis_rollback_exercise_handler.Ticket.objects.filter")
@patch("backend.flow.signal.redis_rollback_exercise_handler.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_ignores_non_drill_or_non_terminal(mock_wakeup, mock_ticket_filter):
    mock_ticket_filter.return_value.only.return_value.first.return_value = MagicMock(
        ticket_type=TicketType.REDIS_DATA_STRUCTURE
    )
    redis_data_structure_task_delete_callback_handler(
        node_id="node_id",
        root_id="child_root_id",
        status=StateType.FINISHED,
        ticket_id=2,
    )
    mock_wakeup.assert_not_called()

    mock_ticket_filter.return_value.only.return_value.first.return_value = MagicMock(
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE
    )
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id="child_root_id",
        status=StateType.RUNNING,
        ticket_id=1,
    )
    mock_wakeup.assert_not_called()


@patch("backend.flow.signal.redis_rollback_exercise_handler.Ticket.objects.filter")
@patch("backend.flow.signal.redis_rollback_exercise_handler.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_no_ticket_id_returns_early(mock_wakeup, mock_ticket_filter):
    """When ticket_id is 0 (falsy), the handler should return early without querying Ticket."""
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id="child_root_id",
        status=StateType.FINISHED,
        ticket_id=0,
    )
    mock_ticket_filter.assert_not_called()
    mock_wakeup.assert_not_called()


@patch("backend.flow.signal.redis_rollback_exercise_handler.Ticket.objects.filter")
@patch("backend.flow.signal.redis_rollback_exercise_handler.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_ticket_not_found_returns_early(mock_wakeup, mock_ticket_filter):
    """When ticket is not found in DB, handler should return without calling wakeup."""
    mock_ticket_filter.return_value.only.return_value.first.return_value = None
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id="child_root_id",
        status=StateType.FINISHED,
        ticket_id=999,
    )
    mock_wakeup.assert_not_called()


# ==================== _resolve_runner_node_id ====================


@patch("backend.flow.signal.redis_rollback_exercise_handler.BambooEngine.get_node_output_data")
@patch("backend.flow.signal.redis_rollback_exercise_handler.FlowNode.objects.filter")
def test_resolve_runner_node_id_scan(mock_node_filter, mock_get_node_output):
    mock_node_filter.return_value.order_by.return_value.values_list.return_value = ["node_1", "node_2"]
    mock_get_node_output.return_value = MagicMock(data={"child_root_id": "child_root_id"})

    node_id = _resolve_runner_node_id(parent_root_id="parent_root_id", child_root_id="child_root_id")

    assert node_id == "node_1"
    mock_node_filter.assert_called_once_with(
        root_id="parent_root_id", status__in=[StateType.RUNNING, StateType.CREATED, StateType.READY]
    )


@patch("backend.flow.signal.redis_rollback_exercise_handler.FlowNode.objects.filter")
def test_resolve_runner_node_id_no_candidates_returns_none(mock_node_filter):
    """When no candidate nodes exist, should return None."""
    mock_node_filter.return_value.order_by.return_value.values_list.return_value = []

    node_id = _resolve_runner_node_id(parent_root_id="parent_root_id", child_root_id="child_root_id")

    assert node_id is None


@patch("backend.flow.signal.redis_rollback_exercise_handler.BambooEngine.get_node_output_data")
@patch("backend.flow.signal.redis_rollback_exercise_handler.FlowNode.objects.filter")
def test_resolve_runner_node_id_no_matching_output_returns_none(mock_node_filter, mock_get_node_output):
    """When no candidate node outputs match child_root_id, should return None."""
    mock_node_filter.return_value.order_by.return_value.values_list.return_value = ["node_1", "node_2"]
    mock_get_node_output.return_value = MagicMock(data={"child_root_id": "other_child_id"})

    node_id = _resolve_runner_node_id(parent_root_id="parent_root_id", child_root_id="child_root_id")

    assert node_id is None
    assert mock_get_node_output.call_count == 2


@patch("backend.flow.signal.redis_rollback_exercise_handler.BambooEngine.get_node_output_data")
@patch("backend.flow.signal.redis_rollback_exercise_handler.FlowNode.objects.filter")
def test_resolve_runner_node_id_output_exception_continues(mock_node_filter, mock_get_node_output):
    """When get_node_output_data raises for one node, should continue scanning others."""
    mock_node_filter.return_value.order_by.return_value.values_list.return_value = ["node_1", "node_2"]
    mock_get_node_output.side_effect = [
        Exception("node_1 failed"),
        MagicMock(data={"child_root_id": "child_root_id"}),
    ]

    node_id = _resolve_runner_node_id(parent_root_id="parent_root_id", child_root_id="child_root_id")

    assert node_id == "node_2"
