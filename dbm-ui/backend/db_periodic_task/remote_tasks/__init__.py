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

from django.db import transaction
from django_celery_beat.models import PeriodicTask

from backend.db_periodic_task.constants import PeriodicTaskType
from backend.db_periodic_task.models import DBPeriodicTask
from backend.db_periodic_task.remote_tasks.register import registered_remote_tasks, register_from_remote



DBPeriodicTask.delete_legacy_periodic_task(registered_remote_tasks, PeriodicTaskType.REMOTE.value)
register_from_remote()
