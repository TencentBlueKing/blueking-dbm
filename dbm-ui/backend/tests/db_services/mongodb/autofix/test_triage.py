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

from backend.db_services.mongodb.autofix.triage import (
    ACTION_FIX_STATUS,
    ACTION_IGNORE,
    ACTION_RELOAD,
    ACTION_REPLACE,
    CONFIRM_AUTH_ERROR,
    CONFIRM_DISK_DEAD,
    CONFIRM_DISK_RO,
    CONFIRM_LOGIN_OK,
    CONFIRM_MACHINE_DEAD,
    CONFIRM_PROCESS_BAD,
    decide_autofix_action,
    is_drs_auth_error,
)


@pytest.mark.parametrize(
    "disk_rw_ok,gse_alive,datadir_writable,drs_ok,drs_auth_error,action,confirm",
    [
        # 1 disk RO
        (0, True, True, False, False, ACTION_REPLACE, CONFIRM_DISK_RO),
        # 2 machine dead
        (1, False, None, False, False, ACTION_REPLACE, CONFIRM_MACHINE_DEAD),
        (-1, False, None, False, False, ACTION_REPLACE, CONFIRM_MACHINE_DEAD),
        # 3 disk dead (gse ok, write fail)
        (1, True, False, False, False, ACTION_REPLACE, CONFIRM_DISK_DEAD),
        (None, True, False, True, False, ACTION_REPLACE, CONFIRM_DISK_DEAD),
        # 6 auth error (before process_bad)
        (1, True, True, False, True, ACTION_IGNORE, CONFIRM_AUTH_ERROR),
        (-1, True, None, False, True, ACTION_IGNORE, CONFIRM_AUTH_ERROR),
        # 4 process bad
        (1, True, True, False, False, ACTION_RELOAD, CONFIRM_PROCESS_BAD),
        (None, True, None, False, False, ACTION_RELOAD, CONFIRM_PROCESS_BAD),
        # 5 login ok → 状态修复（非重启）
        (1, True, True, True, False, ACTION_FIX_STATUS, CONFIRM_LOGIN_OK),
        (-1, True, None, True, False, ACTION_FIX_STATUS, CONFIRM_LOGIN_OK),
    ],
)
def test_decide_autofix_action(disk_rw_ok, gse_alive, datadir_writable, drs_ok, drs_auth_error, action, confirm):
    got_action, got_confirm = decide_autofix_action(
        disk_rw_ok=disk_rw_ok,
        gse_alive=gse_alive,
        datadir_writable=datadir_writable,
        drs_ok=drs_ok,
        drs_auth_error=drs_auth_error,
    )
    assert got_action == action
    assert got_confirm == confirm


def test_disk_ro_beats_gse_and_drs():
    action, confirm = decide_autofix_action(0, False, False, False, True)
    assert action == ACTION_REPLACE
    assert confirm == CONFIRM_DISK_RO


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Authentication failed", True),
        ("SCRAM authentication failed", True),
        ("not authorized on admin", True),
        ("connection refused", False),
        ("timeout", False),
        ("", False),
    ],
)
def test_is_drs_auth_error(message, expected):
    assert is_drs_auth_error(message) is expected
