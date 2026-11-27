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

from backend.exec_host.models import ExecHost


@admin.register(ExecHost)
class ExecHostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "ip",
        "bk_biz_id",
        "bk_cloud_id",
        "db_type",
        "purpose",
        "status",
        "deploy_path",
        "version",
        "creator",
        "create_at",
        "updater",
        "update_at",
    )
    list_filter = ("status", "db_type", "purpose", "bk_cloud_id")
    search_fields = ("name", "ip", "bk_biz_id", "purpose", "version")
    readonly_fields = ("create_at", "update_at")
