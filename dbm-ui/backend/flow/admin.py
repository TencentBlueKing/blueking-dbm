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


@admin.register(models.FlowTree)
class FlowTreeAdmin(admin.ModelAdmin):
    list_display = ("bk_biz_id", "uid", "root_id", "status", "created_by", "created_at", "updated_at")
    list_filter = ("bk_biz_id", "ticket_type", "status")
    search_fields = ("uid", "root_id")


@admin.register(models.FlowNode)
class FlowNodeAdmin(admin.ModelAdmin):
    list_display = ("uid", "root_id", "node_id", "version_id", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = (
        "uid",
        "root_id",
        "node_id",
        "version_id",
    )
