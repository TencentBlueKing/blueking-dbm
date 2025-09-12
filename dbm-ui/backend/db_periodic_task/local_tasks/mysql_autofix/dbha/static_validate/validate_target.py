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

from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_monitor.models import MySQLDBHAEvent


def validate_target(events: List[MySQLDBHAEvent]) -> List[MySQLDBHAEvent]:
    """
    验证关联对象状态
    """
    res = []
    for ev in events:
        try:
            ev.instance()
            res.append(ev)
        except Cluster.DoesNotExist:
            ev.failed_validate_it(f"cluster not found for {ev}")
        except ProxyInstance.DoesNotExist:
            ev.failed_validate_it(f"unavailable online {ev.machine_type} not found for {ev}")
        except StorageInstance.DoesNotExist:
            ev.failed_validate_it(f"unavailable online {ev.machine_type} slave not found for {ev}")

    return res
