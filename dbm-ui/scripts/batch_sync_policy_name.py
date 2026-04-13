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
from collections import defaultdict

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.prod")
django.setup()


def sync_policy_name():
    from backend.db_monitor.models import MonitorPolicy
    from backend.db_meta.models import AppCache

    all_apps = AppCache.objects.all()
    biz_id_app_map = {app.bk_biz_id: app for app in all_apps}

    parent_policies = MonitorPolicy.objects.filter(parent_id=0)

    updated_count = 0

    for policy in parent_policies:
        sub_policies = list(
            MonitorPolicy.objects.filter(parent_id=policy.id).order_by("create_at")
        )
        if not sub_policies:
            continue

        # 分组处理
        biz_son_policy_map = defaultdict(list)
        policies_to_update = []

        # 第一步：收集所有需要更新的子策略及其新名称
        for sub in sub_policies:
            app = biz_id_app_map.get(sub.bk_biz_id)
            if not app:
                continue

            app_tag = app.db_app_abbr or str(app.bk_biz_id)

            if sub.target_level == "appid":
                new_name = f"DBM#{app_tag} {policy.name}"
                policies_to_update.append((sub, new_name))
            else:
                biz_son_policy_map[sub.bk_biz_id].append(sub)

        # 第二步：处理非 appid 的子策略，生成带编号的名称
        for biz_id, policies in biz_son_policy_map.items():
            app = biz_id_app_map.get(biz_id)
            if not app:
                continue
            app_tag = app.db_app_abbr or str(biz_id)

            for idx, son in enumerate(policies, start=1):
                new_name = f"DBM#{app_tag} {policy.name} - 子策略{idx}"
                policies_to_update.append((son, new_name))

        # 逐个更新
        for policy_obj, new_name in policies_to_update:

            old_name = policy_obj.name
            policy_obj.name = new_name
            policy_obj.details["name"] = new_name

            try:
                policy_obj.save()
                updated_count += 1
                print(f"Updated policy {policy_obj.id}: '{old_name}' → '{new_name}'")
            except Exception as e:
                print(f"Failed to update policy id={policy_obj.id} (name: {new_name}): {e}")

    print(f"Sync completed. Total updated policies: {updated_count}", )
