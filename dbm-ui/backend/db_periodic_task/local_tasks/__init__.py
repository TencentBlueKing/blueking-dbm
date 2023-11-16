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

from backend.db_periodic_task.local_tasks.check_checksum import *
from backend.db_periodic_task.local_tasks.db_meta import *
from backend.db_periodic_task.local_tasks.db_monitor import *
from backend.db_periodic_task.local_tasks.db_proxy import *
from backend.db_periodic_task.local_tasks.dbmon_heartbeat import *
from backend.db_periodic_task.local_tasks.redis_autofix import *
from backend.db_periodic_task.local_tasks.redis_backup import *
from backend.db_periodic_task.local_tasks.redis_clusternodes_update import *
from backend.db_periodic_task.local_tasks.ticket import *
from backend.db_periodic_task.models import DBPeriodicTask

from ..constants import PeriodicTaskType
from .register import registered_local_tasks

# 删除过期的本地周期任务
DBPeriodicTask.delete_legacy_periodic_task(registered_local_tasks, PeriodicTaskType.LOCAL.value)
