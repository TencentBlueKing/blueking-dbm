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
        # "is_synced",
        "sync_at",
        "event_count",
        # "dispatch_group_id",
    )
    list_filter = ("bk_biz_id", "db_type")
    search_fields = ("name",)
