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

"""当天失败城市的重试条件和告警正文。"""


class _Run(object):
    def __init__(self, flow_result, hosts=None, resource_returned=False, error_message="", phase="resource_apply"):
        self.flow_result = flow_result
        self.hosts = hosts if hosts is not None else []
        self.resource_returned = resource_returned
        self.error_message = error_message
        self.phase = phase
        self.dbha_result = "unknown"


def test_not_started_city_can_start(drill_record):
    start_it, reason = drill_record.drill_start_decision([])
    assert start_it is True
    assert reason == "not_started"


def test_failed_without_hosts_can_retry(drill_record):
    runs = [_Run(drill_record.RESULT_FAILED, error_message="资源不足")]
    start_it, reason = drill_record.drill_start_decision(runs)
    assert start_it is True
    assert reason == "failed"


def test_failed_after_hosts_returned_can_retry(drill_record):
    runs = [
        _Run(
            drill_record.RESULT_FAILED,
            hosts=[{"ip": "1.0.0.1"}],
            resource_returned=True,
            phase="teardown",
        )
    ]
    start_it, reason = drill_record.drill_start_decision(runs)
    assert start_it is True
    assert reason == "failed"


def test_hosts_still_held_stops_retry(drill_record):
    runs = [_Run(drill_record.RESULT_FAILED, hosts=[{"ip": "1.0.0.1"}], phase="apply")]
    start_it, reason = drill_record.drill_start_decision(runs)
    assert start_it is False
    assert reason == "hosts_held"


def test_older_held_hosts_block_a_new_day(drill_record):
    held = [_Run(drill_record.RESULT_FAILED, hosts=[{"ip": "1.0.0.1"}])]
    start_it, reason = drill_record.drill_start_decision([], open_runs=held)
    assert start_it is False
    assert reason == "hosts_held"


def test_running_city_is_not_started_again(drill_record):
    runs = [_Run(drill_record.RESULT_RUNNING, hosts=[{"ip": "1.0.0.1"}])]
    start_it, reason = drill_record.drill_start_decision(runs)
    assert start_it is False
    assert reason == "running"


def test_passed_city_is_done(drill_record):
    assert drill_record.drill_start_decision([_Run(drill_record.RESULT_PASSED)]) == (False, "done")
    passed_with_skips = [_Run(drill_record.RESULT_PASSED_WITH_SKIPS)]
    assert drill_record.drill_start_decision(passed_with_skips) == (False, "done")
    assert drill_record.city_day_status([_Run(drill_record.RESULT_PASSED)]) is None


def test_attempt_limit_stops_retry(drill_record):
    runs = [_Run(drill_record.RESULT_FAILED) for _ in range(drill_record.MAX_DAILY_ATTEMPTS)]
    start_it, reason = drill_record.drill_start_decision(runs)
    assert start_it is False
    assert reason == "attempt_limit"


def test_skip_rows_do_not_count_as_attempts(drill_record):
    runs = [_Run(drill_record.RESULT_FAILED)] + [_Run(drill_record.RESULT_SKIPPED) for _ in range(5)]
    start_it, reason = drill_record.drill_start_decision(runs)
    assert start_it is True
    assert reason == "failed"


def test_alert_body_summarizes_latest_results(drill_alert):
    body = drill_alert.build_alert_body(
        [
            {
                "city": "上海",
                "cluster_type": "tendbha",
                "version": "v1",
                "phase": "done",
                "flow_result": "passed",
                "dbha_result": "switched",
                "attempts": 1,
                "reason": "done",
                "error_message": "",
            },
            {
                "city": "上海",
                "cluster_type": "tendbcluster",
                "version": "v2",
                "phase": "resource_apply",
                "flow_result": "failed",
                "dbha_result": "unknown",
                "attempts": 2,
                "reason": "failed",
                "error_message": "资源不足",
            },
        ]
    )
    assert "启用 2，完成 1，失败 1，进行中 0，未发起 0，开关关闭 0" in body
    assert "上海 tendbha v1 done passed switched 1" in body
    assert "上海 tendbcluster v2 resource_apply failed unknown 2" in body
    assert "资源不足" in body


def test_alert_task_stays_off(drill_alert):
    assert drill_alert.ALERT_ENABLED is False
    assert drill_alert.mysql_failover_drill_v1_alert_task() is None
