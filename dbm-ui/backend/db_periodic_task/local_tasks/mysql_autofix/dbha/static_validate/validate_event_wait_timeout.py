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
import datetime
from typing import List

from django.utils import timezone

from backend.db_monitor.models import MySQLDBHAEvent


def validate_event_wait_timeout(events: List[MySQLDBHAEvent]) -> List[MySQLDBHAEvent]:
    """
    校验等待超时
    """
    timeout_line = timezone.now() - datetime.timedelta(minutes=15)
    res = []
    for ev in events:
        if ev.event_create_time >= timeout_line:
            res.append(ev)
        else:
            ev.failed_validate_it("wait timeout")

    return res
