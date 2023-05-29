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
from unittest.mock import patch

import pytest

from backend.db_periodic_task.constants import PeriodicTaskType
from backend.db_periodic_task.models import DBPeriodicTask
from backend.tests.mock_data.components.celery_service import REMOTE_API_LIST, CeleryServiceApiMock

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")


class TestRegisterRemoteTasks:
    @patch("backend.components.celery_service.client.CeleryServiceApi", CeleryServiceApiMock)
    def test_register_remote_tasks(self):
        from backend.db_periodic_task.remote_tasks.register import register_from_remote, registered_remote_tasks

        register_from_remote()
        assert len(registered_remote_tasks) == len(REMOTE_API_LIST)
        assert DBPeriodicTask.objects.filter(task_type=PeriodicTaskType.REMOTE.value).count() == len(REMOTE_API_LIST)

    def test_register_local_tasks(self):
        from backend.db_periodic_task.local_tasks import register_periodic_task

        @register_periodic_task(run_every=1)
        def demo_task():
            return "hello, world!"

        assert DBPeriodicTask.objects.filter(task_type=PeriodicTaskType.LOCAL, name__contains="demo_task").count()
