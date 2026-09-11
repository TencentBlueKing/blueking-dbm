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
from typing import Optional, Tuple

# follow-up actions
ACTION_REPLACE = "replace"
ACTION_RELOAD = "reload"
ACTION_FIX_STATUS = "fix_status"
ACTION_IGNORE = "ignore"

# confirm_result values mirror MongoAutofixConfirmResult (keep strings for pure-unit tests)
CONFIRM_DISK_RO = "disk_ro"
CONFIRM_MACHINE_DEAD = "machine_dead"
CONFIRM_DISK_DEAD = "disk_dead"
CONFIRM_PROCESS_BAD = "process_bad"
CONFIRM_LOGIN_OK = "login_ok"
CONFIRM_AUTH_ERROR = "auth_error"


def decide_autofix_action(
    disk_rw_ok: Optional[int],
    gse_alive: bool,
    datadir_writable: Optional[bool],
    drs_ok: bool,
    drs_auth_error: bool,
) -> Tuple[str, str]:
    """
    PRE triage decision (pure function).

    Order:
    1. disk_rw_ok == 0 → REPLACE / disk_ro
    2. GSE unreachable → REPLACE / machine_dead
    3. GSE ok but datadir not writable → REPLACE / disk_dead
    4. DRS auth error → IGNORE / auth_error
    5. DRS fail (non-auth) → RELOAD / process_bad
    6. DRS success → FIX_STATUS / login_ok（探测成功只修元数据状态，不重启）

    disk_rw_ok: 1 ok, 0 fail, None/-1 missing (missing does not alone trigger replace)
    datadir_writable: True/False when probed; None means not probed
    """
    if disk_rw_ok == 0:
        return ACTION_REPLACE, CONFIRM_DISK_RO

    if not gse_alive:
        return ACTION_REPLACE, CONFIRM_MACHINE_DEAD

    if datadir_writable is False:
        return ACTION_REPLACE, CONFIRM_DISK_DEAD

    if drs_auth_error:
        return ACTION_IGNORE, CONFIRM_AUTH_ERROR

    if not drs_ok:
        return ACTION_RELOAD, CONFIRM_PROCESS_BAD

    return ACTION_FIX_STATUS, CONFIRM_LOGIN_OK


def is_drs_auth_error(message: str) -> bool:
    """Heuristic: treat common Mongo auth failure strings as auth errors."""
    if not message:
        return False
    lowered = message.lower()
    needles = (
        "authentication failed",
        "auth failed",
        "not authorized",
        "unauthorized",
        "authenticationfailed",
        "scram",
        "requires authentication",
        "auth exception",
    )
    return any(n in lowered for n in needles)
