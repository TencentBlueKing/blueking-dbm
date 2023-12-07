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


@admin.register(models.app.App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("bk_biz_id", "bk_set_id")
    list_filter = ("bk_biz_id",)
    search_fields = ("bk_set_id",)


@admin.register(models.app.AppCache)
class AppCacheAdmin(admin.ModelAdmin):
    list_display = ("bk_biz_id", "bk_biz_name", "db_app_abbr")
    list_filter = ("bk_biz_name",)
    search_fields = ("bk_biz_id", "bk_biz_name", "db_app_abbr")


@admin.register(models.city_map.LogicalCity)
class LogicalCityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )
    search_fields = ("name",)


@admin.register(models.city_map.BKCity)
class BKCityAdmin(admin.ModelAdmin):
    list_display = ("bk_idc_city_id", "bk_idc_city_name", "logical_city_id", "logical_city")
    list_filter = ("logical_city",)
    search_fields = ("bk_idc_city_name",)


@admin.register(models.cluster.Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ("name", "bk_biz_id", "cluster_type", "db_module_id", "immute_domain")
    list_filter = ("bk_biz_id", "cluster_type")
    search_fields = ("name", "immute_domain")


@admin.register(models.cluster_entry.ClusterEntry)
class ClusterEntryAdmin(admin.ModelAdmin):
    list_display = ("cluster", "cluster_entry_type", "entry")
    list_filter = ("cluster_entry_type",)
    search_fields = ("entry",)


@admin.register(models.db_module.DBModule)
class DBModuleAdmin(admin.ModelAdmin):
    list_display = ("bk_biz_id", "db_module_name", "db_module_id")
    list_filter = ("bk_biz_id", "cluster_type")
    search_fields = ("db_module_name",)


@admin.register(models.db_module.BKModule)
class BKModuleAdmin(admin.ModelAdmin):
    list_display = ("bk_module_id", "db_module_id", "machine_type")
    list_filter = ("machine_type",)
    search_fields = ("db_module_id",)


@admin.register(models.instance.StorageInstance)
class StorageInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "machine",
        "port",
        "db_module_id",
        "bk_biz_id",
        "access_layer",
        "machine_type",
        "instance_role",
        "instance_inner_role",
        "cluster_type",
        "status",
    )
    list_filter = (
        "status",
        "access_layer",
        "machine_type",
        "instance_role",
        "instance_inner_role",
        "cluster_type",
        "status",
        "bk_biz_id",
    )
    search_fields = ("machine__ip",)


@admin.register(models.instance.ProxyInstance)
class ProxyInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "machine",
        "port",
        "db_module_id",
        "bk_biz_id",
        "access_layer",
        "machine_type",
        "cluster_type",
        "status",
    )
    list_filter = (
        "status",
        "access_layer",
        "machine_type",
        "cluster_type",
        "status",
        "bk_biz_id",
    )
    search_fields = ("machine__ip",)


@admin.register(models.machine.Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("ip", "bk_biz_id", "access_layer", "machine_type", "cluster_type", "bk_city")
    list_filter = ("bk_biz_id", "access_layer", "machine_type", "cluster_type", "bk_city")
    search_fields = ("ip", "db_module_id")


@admin.register(models.storage_instance_tuple.StorageInstanceTuple)
class StorageInstanceTupleAdmin(admin.ModelAdmin):
    list_display = (
        "ejector",
        "receiver",
    )
    search_fields = ("ejector__machine__ip", "receiver__machine__ip")


@admin.register(models.spec.Spec)
class SpecAdmin(admin.ModelAdmin):
    list_display = (
        "spec_name",
        "spec_cluster_type",
        "spec_machine_type",
        "cpu",
        "mem",
        "device_class",
        "storage_spec",
    )
    search_fields = ("spec_name", "spec_cluster_type", "spec_machine_type")
