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

from .models.tb_tendis_dts_job import TbTendisDTSJob
from .models.tb_tendis_dts_task import TbTendisDtsTask


@admin.register(TbTendisDTSJob)
class TendisDtsJobAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TbTendisDTSJob._meta.get_fields()]
    search_fields = ("app", "user", "src_cluster", "dst_cluster", "status")
    list_filter = ("app", "user", "src_cluster", "dst_cluster", "status")


@admin.register(TbTendisDtsTask)
class TendisDtsTaskAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TbTendisDtsTask._meta.get_fields()]
    search_fields = ("src_cluster", "src_ip", "src_port", "dst_cluster", "task_type", "status", "sync_operate")
    list_filter = ("src_cluster", "src_ip", "src_port", "dst_cluster", "task_type", "status", "sync_operate")
