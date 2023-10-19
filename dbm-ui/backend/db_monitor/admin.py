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
from django.contrib import admin

from . import models


@admin.register(models.MonitorPolicy)
class MonitorPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "parent_id",
        "id",
        "monitor_policy_id",
        "name",
        "db_type",
        "bk_biz_id",
        "target_level",
        "target_keyword",
        "is_enabled",
        "sync_at",
        "event_count",
    )
    list_filter = ("bk_biz_id", "db_type")
    search_fields = ("name",)


@admin.register(models.DutyRule)
class DutyRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "monitor_duty_rule_id",
        "priority",
        "is_enabled",
        "effective_time",
        "end_time",
        "category",
        "db_type",
    )
    list_filter = ("category", "db_type")
    search_fields = ("name",)


@admin.register(models.NoticeGroup)
class NoticeGroupAdmin(admin.ModelAdmin):
    list_display = (
        "bk_biz_id",
        "name",
        "monitor_group_id",
        "monitor_duty_rule_id",
        "db_type",
        "is_built_in",
        "sync_at",
        "dba_sync",
    )
    list_filter = ("db_type", "is_built_in", "dba_sync")
    search_fields = ("name",)
