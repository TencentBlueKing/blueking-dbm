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

import pytest

pytestmark = pytest.mark.django_db


def test_mongodb_affinity_check_task_entry(mongodb_tasks_task_module):
    with patch.object(mongodb_tasks_task_module.TaskRecordRepo, "execute_task_with_record") as execute_mock:
        mongodb_tasks_task_module.mongodb_affinity_check_task()

    assert execute_mock.called
    kwargs = execute_mock.call_args.kwargs
    assert kwargs["db_type"] == "mongodb"
    assert kwargs["task_name"] == "mongodb_affinity_check_task"
    assert kwargs["task_type"] == "affinity"
    assert kwargs["check_task_instance"].__class__.__name__ == "CheckMongodbAffinityTask"
