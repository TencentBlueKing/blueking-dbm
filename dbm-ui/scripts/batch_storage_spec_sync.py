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
from backend.constants import INT_MAX

os.environ.setdefault('DJANGO_SETTINGS_MODULE', "config.prod")
django.setup()  # 关键：加载应用注册表


def sync_storage_spec():
    from backend.db_meta.models.spec import Spec
    with transaction.atomic():
        all_spec = Spec.objects.all()
        for spec in all_spec:
            new_storage_spec = []
            for storage_spec in spec.storage_spec:
                if storage_spec.get("min") and storage_spec.get("max"):
                    new_storage_spec.append(storage_spec)
                    continue
                storage_spec["min"] = storage_spec["size"] if storage_spec.get("size") else storage_spec.get("min", 1)
                storage_spec["max"] = storage_spec["max"] if storage_spec.get("max") else INT_MAX
                new_storage_spec.append(storage_spec)
            spec.storage_spec = new_storage_spec
            spec.save()


if __name__ == '__main__':
    sync_storage_spec()
