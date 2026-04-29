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
import json
import os
import datetime
import django

from copy import deepcopy
from django.db import transaction
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', "config.prod")
django.setup()  # 关键：加载应用注册表


def sync_appcache_managed():
    from backend.configuration.models import DBAdministrator
    from backend.db_meta.models import AppCache, Cluster

    with transaction.atomic():
        all_biz_ids = set(AppCache.objects.all().values_list("bk_biz_id", flat=True))
        managed_ids = set(Cluster.objects.exclude(phase="destroy").all().values_list("bk_biz_id", flat=True))

        managed_biz_ids = all_biz_ids & managed_ids

        AppCache.objects.filter(bk_biz_id__in=list(managed_biz_ids)).update(
            status="managed",
            managed_time=datetime.datetime.now(timezone.utc)
        )

    with transaction.atomic():
        for dba in DBAdministrator.objects.all():
            old_users = deepcopy(dba.users)
            if len(old_users) >= 3:
                continue
            if len(old_users) == 2:
                old_users.append(old_users[0])
            if len(old_users) == 1:
                old_users = old_users + [old_users[0], old_users[0]]
            dba.users = old_users
            dba.save()
