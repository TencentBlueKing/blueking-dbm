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
import pytest

from backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.enums import (
    BkJobHostErrorCode,
    BkJobInstanceStatus,
    BkJobStepStatus,
)

UNKNOWN_CODE = -999


@pytest.mark.parametrize(
    "enum_cls,known_value,known_member",
    [
        (BkJobInstanceStatus, 3, BkJobInstanceStatus.SUCCESS),
        (BkJobStepStatus, 9, BkJobStepStatus.SUCCESS),
        (BkJobHostErrorCode, 11, BkJobHostErrorCode.TASK_FAILED),
    ],
)
def test_known_code(enum_cls, known_value, known_member):
    assert enum_cls(known_value) is known_member


@pytest.mark.parametrize(
    "enum_cls",
    [BkJobInstanceStatus, BkJobStepStatus, BkJobHostErrorCode],
)
def test_unknown_code_fallback(enum_cls):
    status = enum_cls(UNKNOWN_CODE)
    assert status.value == UNKNOWN_CODE
    assert enum_cls.get_choice_label(UNKNOWN_CODE) == f"未知状态码({UNKNOWN_CODE})"
    assert enum_cls(UNKNOWN_CODE) is status
