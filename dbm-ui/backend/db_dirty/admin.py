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


@admin.register(models.DirtyMachine)
class DirtyMachineAdmin(admin.ModelAdmin):
    list_display = ("ip", "bk_biz_id", "bk_host_id", "flow", "ticket")
    list_filter = ("ip", "bk_biz_id", "bk_host_id", "flow", "ticket")
    search_fields = ("ip", "bk_biz_id", "bk_host_id", "flow", "ticket")
