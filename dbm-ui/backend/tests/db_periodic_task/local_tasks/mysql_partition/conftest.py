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
import importlib

import pytest

_MODULE = "backend.db_periodic_task.local_tasks.mysql_partition.retry_partition_task"


@pytest.fixture(scope="module")
def retry_mod(django_db_setup, django_db_blocker):
    """惰性导入。模块顶层会注册周期任务并触发 local_tasks 全量加载。"""
    with django_db_blocker.unblock():
        return importlib.import_module(_MODULE)
