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
from unittest.mock import patch

from backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.enums import BkJobInstanceStatus
from backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.query_result import query_result


@patch("backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.query_result.JobApi.batch_get_job_instance_ip_log")
@patch("backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.query_result.JobApi.get_job_instance_status")
def test_empty_step_instance_list_returns_intermediate_state(mock_get_status, mock_get_log):
    mock_get_status.return_value = {
        "finished": False,
        "job_instance": {"status": BkJobInstanceStatus.RUNNING.value},
        "step_instance_list": [],
    }

    result = query_result("biz_set", 1, 100)

    assert result == {
        "job_finished": False,
        "job_status": BkJobInstanceStatus.RUNNING,
        "step_instance_id": None,
        "host_results": [],
    }
    mock_get_log.assert_not_called()


@patch("backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.query_result.JobApi.batch_get_job_instance_ip_log")
@patch("backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.query_result.JobApi.get_job_instance_status")
def test_empty_step_ip_result_list_skips_log_fetch(mock_get_status, mock_get_log):
    mock_get_status.return_value = {
        "finished": False,
        "job_instance": {"status": BkJobInstanceStatus.RUNNING.value},
        "step_instance_list": [{"step_instance_id": 200, "step_ip_result_list": []}],
    }

    result = query_result("biz_set", 1, 100)

    assert result["job_finished"] is False
    assert result["step_instance_id"] == 200
    assert result["host_results"] == []
    mock_get_log.assert_not_called()
