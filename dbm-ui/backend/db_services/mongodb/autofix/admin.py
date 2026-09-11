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
from django.utils.translation import gettext_lazy as _

from . import models


@admin.register(models.MongoAutofixCtl)
class MongoAutofixCtlAdmin(admin.ModelAdmin):
    list_display = ("id", "bk_biz_id", "bk_cloud_id", "ctl_name", "ctl_value", "updater", "update_at")
    list_filter = ("ctl_name", "bk_biz_id", "bk_cloud_id")
    search_fields = ("ctl_name", "ctl_value", "bk_biz_id")
    ordering = ("-update_at",)
    list_per_page = 50


@admin.register(models.MongoAutofixCore)
class MongoAutofixCoreAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bk_biz_id",
        "immute_domain",
        "ip",
        "deal_status",
        "confirm_result",
        "pre_ticket_id",
        "ticket_id",
        "disk_rw_ok",
        "bk_city",
        "bk_sub_zone_id",
        "detected_at",
        "update_at",
    )
    list_filter = ("deal_status", "confirm_result", "cluster_type", "bk_biz_id", "bk_cloud_id")
    search_fields = ("ip", "immute_domain", "cluster_id", "bk_host_id", "pre_ticket_id", "ticket_id", "status_version")
    readonly_fields = ("create_at", "update_at", "detected_at")
    ordering = ("-id",)
    list_per_page = 50

    fieldsets = (
        (
            _("集群"),
            {"fields": ("bk_cloud_id", "bk_biz_id", "cluster_id", "cluster_ids", "cluster_type", "immute_domain")},
        ),
        (_("故障机"), {"fields": ("ip", "bk_host_id", "ports", "roles", "fault_machines", "bk_city", "bk_sub_zone_id")}),
        (
            _("自愈状态"),
            {
                "fields": (
                    "deal_status",
                    "confirm_result",
                    "disk_rw_ok",
                    "status_version",
                    "pre_ticket_id",
                    "ticket_id",
                    "detected_at",
                )
            },
        ),
        (_("审计"), {"fields": ("creator", "create_at", "updater", "update_at")}),
    )


@admin.register(models.MongoIgnoreAutofix)
class MongoIgnoreAutofixAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bk_biz_id",
        "immute_domain",
        "ip",
        "ignore_msg",
        "cluster_id",
        "cluster_type",
        "create_at",
    )
    list_filter = ("ignore_msg", "cluster_type", "bk_biz_id", "bk_cloud_id")
    search_fields = ("ip", "immute_domain", "ignore_msg", "cluster_id", "bk_host_id")
    readonly_fields = ("create_at", "update_at")
    ordering = ("-id",)
    list_per_page = 50


@admin.register(models.MongoAutofixLog)
class MongoAutofixLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "core_id",
        "event",
        "ip",
        "immute_domain",
        "deal_status",
        "confirm_result",
        "pre_ticket_id",
        "ticket_id",
        "message",
        "create_at",
    )
    list_filter = ("event", "deal_status", "bk_biz_id", "bk_cloud_id")
    search_fields = ("ip", "immute_domain", "message", "core_id", "pre_ticket_id", "ticket_id")
    readonly_fields = ("create_at", "update_at")
    ordering = ("-id",)
    list_per_page = 50
