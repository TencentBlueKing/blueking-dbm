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

from backend.db_services.mongodb.autofix.ctl import is_followup_need_approval
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import _apply_followup_approval_flags


def test_followup_need_approval_default_on():
    with patch(
        "backend.db_services.mongodb.autofix.ctl.get_ctl_value",
        return_value="on",
    ):
        assert is_followup_need_approval() is True
        details = _apply_followup_approval_flags({})
        assert details["need_itsm"] is True
        assert details["need_manual_confirm"] is True


def test_followup_need_approval_off_skips():
    with patch(
        "backend.db_services.mongodb.autofix.ctl.get_ctl_value",
        return_value="off",
    ):
        assert is_followup_need_approval() is False
        details = _apply_followup_approval_flags({})
        assert details["need_itsm"] is False
        assert details["need_manual_confirm"] is False
