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

import logging
from typing import List, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_meta.models.machine import Machine

logger = logging.getLogger("root")


@transaction.atomic
def clear_machine(machines: Optional[List]):
    """
    根据machine信息回收机器相关信息for大数据
    """
    for m in machines:
        try:
            machine = Machine.objects.get(ip=m["ip"], bk_cloud_id=m["bk_cloud_id"])
        except ObjectDoesNotExist:
            logger.warning(f"the machine [{m['bk_cloud_id']}:{m['ip']}] not exist ")
            continue

        proxys = ProxyInstance.objects.filter(machine=machine)
        storages = StorageInstance.objects.filter(machine=machine)

        # 清理proxy相关信息
        for p in proxys:
            p.delete(keep_parents=True)

        # 清理storage相关信息
        for s in storages:
            s.delete(keep_parents=True)

        machine.delete(keep_parents=True)
