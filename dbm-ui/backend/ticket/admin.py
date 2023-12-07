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


@admin.register(models.Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("bk_biz_id", "ticket_type", "status", "creator", "update_at")
    list_filter = ("bk_biz_id", "ticket_type", "status")
    search_fields = ("id",)


@admin.register(models.Flow)
class TicketFlowAdmin(admin.ModelAdmin):
    list_display = ("ticket_id", "flow_type", "flow_alias", "flow_obj_id", "status", "update_at")
    search_fields = ("ticket_id", "flow_obj_id")
    list_filter = ("flow_type", "status")


@admin.register(models.TicketFlowConfig)
class TicketFlowConfigAdmin(admin.ModelAdmin):
    list_display = ("ticket_type", "group", "editable")
    search_fields = ("ticket_type", "group", "editable")
    list_filter = ("group",)
