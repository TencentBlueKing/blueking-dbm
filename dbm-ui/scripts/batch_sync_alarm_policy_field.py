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

from copy import deepcopy
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', "config.prod")
django.setup()  # 关键：加载应用注册表


def compare_complex_lists(list1, list2):
    def normalize(d):
        return json.dumps(d, sort_keys=True, separators=(',', ':'))

    sorted_list1 = sorted([normalize(item) for item in list1])
    sorted_list2 = sorted([normalize(item) for item in list2])

    return sorted_list1 == sorted_list2


def set_test_rules(test_rules):
    for rule in test_rules:
        rule["level"] = str(rule["level"])
        for conf in rule["config"]:
            for c in conf:
                c["threshold"] = str(c["threshold"])
    return test_rules


def set_detects_config(detects_config):
    detects_config["trigger_config"]["count"] = str(detects_config["trigger_config"]["count"])
    detects_config["trigger_config"]["check_window"] = str(detects_config["trigger_config"]["check_window"])
    detects_config["recovery_config"]["check_window"] = str(detects_config["recovery_config"]["check_window"])

    return detects_config


def set_no_data_config(no_data_config):
    no_data_config["continuous"] = str(no_data_config["continuous"])
    no_data_config["level"] = str(no_data_config["level"])
    return no_data_config


def sync_policy_field(policy_ids):
    from backend.db_monitor.models import MonitorPolicy

    with transaction.atomic():
        if policy_ids:
            all_policies = MonitorPolicy.objects.filter(id__in=policy_ids)
        else:
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
                    parent_test_rules = deepcopy(parent_policy.test_rules)
                    sub_test_rules = deepcopy(policy.test_rules)
                    test_rules_is_eq = compare_complex_lists(
                        set_test_rules(sub_test_rules), set_test_rules(parent_test_rules)
                    )

                    parent_detects_config = set_detects_config(deepcopy(parent_policy.detects_config))
                    sub_detects_config = set_detects_config(deepcopy(policy.detects_config))
                    detects_config_is_eq = parent_detects_config == sub_detects_config

                    parent_no_data_config = set_no_data_config(deepcopy(parent_policy.no_data_config))
                    sub_no_data_config = set_no_data_config(deepcopy(policy.no_data_config))
                    no_data_config_is_eq = parent_no_data_config == sub_no_data_config

                    parent_notify_rules = parent_policy.notify_rules[:]
                    sub_notify_rules = policy.notify_rules[:]
                    if "no_data" in parent_notify_rules:
                        parent_notify_rules.remove("no_data")
                    if "no_data" in sub_notify_rules:
                        sub_notify_rules.remove("no_data")
                    notify_rules_is_eq = compare_complex_lists(parent_notify_rules, sub_notify_rules)

                    if test_rules_is_eq and detects_config_is_eq and no_data_config_is_eq and notify_rules_is_eq:
                        policy_tag = "inner"
                    else:
                        print(f"{policy.id}-{test_rules_is_eq}-{detects_config_is_eq}-"
                              f"{no_data_config_is_eq}-{notify_rules_is_eq}")
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
