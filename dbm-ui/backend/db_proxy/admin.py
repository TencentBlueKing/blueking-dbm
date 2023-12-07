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


@admin.register(models.DBCloudProxy)
class DBCloudProxyAdmin(admin.ModelAdmin):
    list_display = ("bk_cloud_id", "internal_address", "external_address")
    list_filter = ("internal_address", "external_address")
    search_fields = ("internal_address", "external_address")


@admin.register(models.DBExtension)
class DBExtensionAdmin(admin.ModelAdmin):
    list_display = ("id", "bk_cloud_id", "extension", "status", "details")
    list_filter = ("bk_cloud_id", "extension", "status")
    search_fields = ("bk_cloud_id", "extension", "status")


@admin.register(models.ClusterExtension)
class ClusterExtensionAdmin(admin.ModelAdmin):
    list_display = ("id", "bk_biz_id", "bk_cloud_id", "ip", "service_type", "cluster_name")
    list_filter = ("bk_biz_id", "bk_cloud_id", "service_type", "cluster_name")
    search_fields = ("bk_biz_id", "bk_cloud_id", "service_type", "cluster_name")
