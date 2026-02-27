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


def sync_policy_field():
    from backend.db_monitor.models import MonitorPolicy

    with transaction.atomic():
        all_policies = MonitorPolicy.objects.all()
        for policy in all_policies:
            if not policy.details:
                continue
            update_data = dict()

            update_data["notify_config"] = {
                "interval_notify_mode": policy.details["notice"]["config"]["interval_notify_mode"],
                "notify_interval": policy.details["notice"]["config"]["notify_interval"],
            }

            agg_info = []

            for query_config in policy.details["items"][0]["query_configs"]:
                agg_info.append({
                    "metric_id": query_config["metric_id"],
                    "agg_interval": query_config.get("agg_interval"),
                    "agg_method": query_config.get("agg_method"),
                    "metric_field": query_config.get("metric_field"),
                    "promql": query_config.get("promql"),
                })
            update_data["agg_info"] = agg_info

            update_data["expression"] = policy.details["items"][0]["expression"]

            query_configs = policy.details["items"][0]["query_configs"]
            policy_type = ""
            if query_configs[0].get("data_source_label") == "prometheus":
                policy_type = "PromQL"
            elif len(query_configs) >= 2:
                policy_type = "multi"
            elif len(query_configs) == 1:
                policy_type = "single"
            update_data["policy_type"] = policy_type
            old_targets = policy.targets
            for target in old_targets:
                if policy_type == "PromQL":
                    if len(target["rule"]["value"]) > 1:
                        target["rule"]["method"] = "=~"
                    elif len(target["rule"]["value"]) <= 1:
                        target["rule"]["method"] = "="
                else:
                    target["rule"]["method"] = "eq"
            update_data["targets"] = old_targets
            if update_data:
                MonitorPolicy.objects.filter(pk=policy.pk).update(**update_data)


if __name__ == '__main__':
    sync_policy_field()
