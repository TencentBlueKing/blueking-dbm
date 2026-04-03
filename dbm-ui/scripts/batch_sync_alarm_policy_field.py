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
import django

from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', "config.prod")
django.setup()  # 关键：加载应用注册表


def compare_complex_lists(list1, list2):
    def normalize(d):
        return json.dumps(d, sort_keys=True, separators=(',', ':'))

    sorted_list1 = sorted([normalize(item) for item in list1])
    sorted_list2 = sorted([normalize(item) for item in list2])

    return sorted_list1 == sorted_list2


def sync_policy_field():
    from backend.db_monitor.models import MonitorPolicy

    with transaction.atomic():
        all_policies = MonitorPolicy.objects.all()
        for policy in all_policies:
            if not policy.details:
                continue
            update_data = dict()

            if policy.target_level == "platform":
                policy_tag = "inner"
            elif policy.target_level == "appid":
                if policy.parent_id:
                    parent_policy = MonitorPolicy.objects.get(id=policy.parent_id)
                    agg_interval_map = {info["metric_id"]: info["agg_interval"] for info in parent_policy.agg_info}

                    test_rules_is_eq = compare_complex_lists(policy.test_rules, parent_policy.test_rules)
                    detects_config_is_eq = policy.detects_config == parent_policy.detects_config
                    no_data_config_is_eq = policy.no_data_config == parent_policy.no_data_config
                    parent_notify_rules = parent_policy.notify_rules
                    sub_notify_rules = policy.notify_rules
                    if "no_data" in parent_notify_rules:
                        parent_notify_rules.remove("no_data")
                    if "no_data" in sub_notify_rules:
                        sub_notify_rules.remove("no_data")
                    notify_rules_is_eq = parent_notify_rules == sub_notify_rules
                    notify_config_is_eq = policy.notify_config == parent_policy.notify_config
                    agg_interval_is_eq = True
                    for info in policy.agg_info:
                        if info["agg_interval"] != agg_interval_map[info["metric_id"]]:
                            agg_interval_is_eq = False

                    if (
                            test_rules_is_eq and detects_config_is_eq and no_data_config_is_eq and
                            notify_rules_is_eq and notify_config_is_eq and agg_interval_is_eq
                    ):
                        policy_tag = "inner"
                    else:
                        policy_tag = "custom"

            else:
                policy_tag = "subord"

            update_data["policy_tag"] = policy_tag

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

            query_configs = policy.details["items"][0]["query_configs"]
            policy_type = ""
            if query_configs[0].get("data_source_label") == "prometheus":
                policy_type = "PromQL"
            elif len(query_configs) >= 2:
                policy_type = "multi"
            elif len(query_configs) == 1:
                policy_type = "single"

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
