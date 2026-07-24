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


@admin.register(models.DBPeriodicTask)
class DBPeriodicTaskAdmin(admin.ModelAdmin):
    list_display = ["name", "task"]
    search_fields = ["name"]
    list_filter = ["task_type", "is_frozen"]
    raw_id_fields = ["task"]


class AuditedDispatchSettingsAdmin(admin.ModelAdmin):
    readonly_fields = ["creator", "create_at", "updater", "update_at"]

    def save_model(self, request, obj, form, change):
        username = request.user.username or "admin"
        if not change:
            obj.creator = username
        obj.updater = username
        super().save_model(request, obj, form, change)


@admin.register(models.DispatchQueueSettings)
class DispatchQueueSettingsAdmin(AuditedDispatchSettingsAdmin):
    list_display = ["namespace", "updater", "update_at"]
    search_fields = ["namespace"]


@admin.register(models.DispatchTaskSettings)
class DispatchTaskSettingsAdmin(AuditedDispatchSettingsAdmin):
    list_display = ["task_key", "queue", "updater", "update_at"]
    search_fields = ["task_key", "queue__namespace"]
    list_filter = ["queue"]
    autocomplete_fields = ["queue"]


@admin.register(models.DispatchQueueRoute)
class DispatchQueueRouteAdmin(AuditedDispatchSettingsAdmin):
    """Route rows are read-only in admin: remap_namespace() is the mutation path."""

    list_display = ["namespace", "redis_alias", "updater", "update_at"]
    search_fields = ["namespace", "redis_alias"]
    readonly_fields = ["namespace", "redis_alias", "creator", "create_at", "updater", "update_at"]

    def has_add_permission(self, request):
        # Routes are created assign-once by routing.assign_route / bootstrap_routes.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
