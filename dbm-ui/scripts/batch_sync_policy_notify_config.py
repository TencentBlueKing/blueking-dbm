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


def sync_policy_group():
    from backend.db_monitor.models import MonitorPolicy

    with transaction.atomic():
        all_policies = MonitorPolicy.objects.all()
        for policy in all_policies:
            if not policy.details:
                continue
            update_data = {}
            notify_config = policy.notify_config
            notify_config["voice_notice"] = policy.details["notice"]["config"].get("voice_notice") or "parallel"
            update_data["notify_config"] = notify_config

            if update_data:
                MonitorPolicy.objects.filter(pk=policy.pk).update(**update_data)


if __name__ == '__main__':
    sync_policy_group()
