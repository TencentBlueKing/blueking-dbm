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
import pytest
from django.db import connections


@pytest.fixture
def parse_result_mod(django_db_setup, django_db_blocker):
    """懒加载 parse_result，避免 collection 阶段触发 local_tasks 全量注册。"""
    with django_db_blocker.unblock():
        from backend.db_periodic_task.local_tasks.mysql_config_ai_inspect import parse_result

        return parse_result


@pytest.fixture
def batch_mod(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from backend.db_periodic_task.local_tasks.mysql_config_ai_inspect import batch

        return batch


@pytest.fixture
def inspect_tasks(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from backend.db_periodic_task.local_tasks.mysql_config_ai_inspect import tasks

        return tasks


@pytest.fixture
def ai_inspect_table(django_db_setup, django_db_blocker):
    """无 migration 时在 report_db 临时建表，供本包 DB 单测使用。"""
    with django_db_blocker.unblock():
        from backend.db_report.models.mysql_config_ai_inspect import MysqlConfigAiInspect

        conn = connections["report_db"]
        table_name = MysqlConfigAiInspect._meta.db_table
        existing = conn.introspection.table_names()
        created = False
        if table_name not in existing:
            with conn.schema_editor() as schema_editor:
                schema_editor.create_model(MysqlConfigAiInspect)
            created = True
        yield MysqlConfigAiInspect
        MysqlConfigAiInspect.objects.all().delete()
        if created:
            with conn.schema_editor() as schema_editor:
                schema_editor.delete_model(MysqlConfigAiInspect)
