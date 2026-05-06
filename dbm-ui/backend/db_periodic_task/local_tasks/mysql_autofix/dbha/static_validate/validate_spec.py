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
from typing import List

from backend.db_meta.models import Machine
from backend.db_monitor.models import MySQLDBHAEvent


def validate_spec(events: List[MySQLDBHAEvent]) -> List[MySQLDBHAEvent]:
    """
    检查机器规格
    """
    res = []
    for ev in events:
        machine_obj = Machine.objects.get(bk_cloud_id=ev.bk_cloud_id, ip=ev.ip)
        if machine_obj.spec_id <= 0:
            ev.failed_validate_it("spec missing")
        else:
            res.append(ev)

    return res
