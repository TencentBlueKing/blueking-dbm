# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

local_tasks 包在 import 时会注册周期任务并访问 DB；仅在解除 django_db 阻塞后再加载容灾演练模块。
"""
import importlib

import pytest


@pytest.fixture(scope="module")
def drill_record(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.mysql_failover_drill_v1.record")


@pytest.fixture(scope="module")
def drill_defaults(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.mysql_failover_drill_v1.defaults")


@pytest.fixture(scope="module")
def drill_alert(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.mysql_failover_drill_v1.alert")
