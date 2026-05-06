# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import os
import django

from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', "config.prod")
django.setup()  # 关键：加载应用注册表


def fix_host_todo_count(username):
    from backend.ticket.models import Todo
    from backend.db_dirty.models import DirtyMachine

    with transaction.atomic():
        todos = Todo.objects.filter(
            operators__contains=username,
            status="TODO",
            type__in=["RECYCLE_HOST", "FAULT_HOST"]
        )

        host_id_map = {}
        host_ids = []

        for todo in todos:
            host_id = todo.context.get("host_id")
            if host_id:
                host_ids.append(host_id)
                host_id_map[host_id] = todo

        if not host_ids:
            return

        existing_host_ids = set(
            DirtyMachine.objects.filter(bk_host_id__in=host_ids)
            .values_list('bk_host_id', flat=True)
        )

        for host_id in host_id_map:
            if host_id not in existing_host_ids:
                print(f'host id: {host_id} is not in DirtyMachine')
                host_id_map[host_id].set_success("admin", "script operate")
