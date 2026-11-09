# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed on the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import importlib

import pytest

_PKG = "backend.db_periodic_task.local_tasks.kafka_check"


# 导入 local_tasks 包会触发所有周期任务注册（写库），所以和其他周期任务测试一样，放在 fixture 里惰性导入
@pytest.fixture(scope="module")
def rule_mod(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(f"{_PKG}.disk_growth_rule")


@pytest.fixture(scope="module")
def check_mod(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(f"{_PKG}.kafka_disk_growth_check")


@pytest.fixture(scope="module")
def ana_mod(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(f"{_PKG}.disk_growth_analysis")


@pytest.fixture(scope="module")
def cov(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(f"{_PKG}.disk_growth_coverage")
