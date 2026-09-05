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
from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from dynamic_raw_id.admin import DynamicRawIDMixin

from backend.db_meta.enums import InstanceStatus

from . import models


class ChangeStatusForm(forms.Form):
    """批量修改实例状态的表单"""

    STATUS_CHOICES = [
        (InstanceStatus.RUNNING.value, "running"),
        (InstanceStatus.UNAVAILABLE.value, "unavailable"),
        (InstanceStatus.RESTORING.value, "restoring"),
    ]
    status = forms.ChoiceField(choices=STATUS_CHOICES, label=_("目标状态"))


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


@admin.register(models.city_map.BKSubzone)
class BKSubzoneAdmin(admin.ModelAdmin):
    list_display = ("bk_city", "bk_sub_zone", "bk_sub_zone_id")
    list_filter = ("bk_city",)
    search_fields = ("bk_sub_zone", "bk_sub_zone_id")


@admin.register(models.cluster.Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ("name", "bk_biz_id", "cluster_type", "db_module_id", "immute_domain")
    list_filter = ("bk_biz_id", "cluster_type")
    search_fields = ("name", "immute_domain")


@admin.register(models.cluster_entry.ClusterEntry)
class ClusterEntryAdmin(DynamicRawIDMixin, admin.ModelAdmin):
    list_display = ("cluster", "cluster_entry_type", "entry")
    list_filter = ("cluster_entry_type",)
    search_fields = ("entry",)
    dynamic_raw_id_fields = ("cluster", "forward_to")


@admin.register(models.db_module.DBModule)
class DBModuleAdmin(admin.ModelAdmin):
    list_display = ("bk_biz_id", "db_module_name", "db_module_id")
    list_filter = ("bk_biz_id", "cluster_type")
    search_fields = ("db_module_name",)


@admin.register(models.instance.StorageInstance)
class StorageInstanceAdmin(DynamicRawIDMixin, admin.ModelAdmin):
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

    dynamic_raw_id_fields = ("machine", "cluster", "bind_entry")
    actions = ["change_status"]

    @admin.action(description=_("批量修改实例状态"))
    def change_status(self, request, queryset):
        """批量修改选中实例的状态（running / unavailable）"""
        form = None

        if "apply" in request.POST:
            form = ChangeStatusForm(request.POST)
            if form.is_valid():
                new_status = form.cleaned_data["status"]
                count = 0
                with transaction.atomic():
                    for instance in queryset:
                        instance.status = new_status
                        instance.updater = request.user.username
                        instance.save(update_fields=["status", "updater", "update_at"])
                        count += 1
                self.message_user(
                    request,
                    _("成功将 %(count)d 个实例的状态修改为 %(status)s") % {"count": count, "status": new_status},
                    messages.SUCCESS,
                )
                return None

        if form is None:
            form = ChangeStatusForm()

        return render(
            request,
            "admin/db_meta/change_storage_instance_status.html",
            context={
                "instances": queryset,
                "form": form,
                "title": _("批量修改实例状态"),
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )


@admin.register(models.instance.ProxyInstance)
class ProxyInstanceAdmin(DynamicRawIDMixin, admin.ModelAdmin):
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
    dynamic_raw_id_fields = ("machine", "cluster", "storageinstance", "bind_entry")


@admin.register(models.machine.Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("ip", "bk_biz_id", "access_layer", "machine_type", "cluster_type", "bk_city")
    list_filter = ("bk_biz_id", "access_layer", "machine_type", "cluster_type", "bk_city")
    search_fields = ("ip", "db_module_id")


@admin.register(models.machine.DeviceClass)
class DeviceClassAdmin(admin.ModelAdmin):
    list_display = ("device_type", "cpu", "mem", "disk")
    search_fields = ("device_type",)


@admin.register(models.storage_instance_tuple.StorageInstanceTuple)
class StorageInstanceTupleAdmin(DynamicRawIDMixin, admin.ModelAdmin):
    list_display = (
        "ejector",
        "receiver",
    )
    search_fields = ("ejector__machine__ip", "receiver__machine__ip")
    dynamic_raw_id_fields = ("ejector", "receiver")


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


@admin.register(models.extra_process.ExtraProcessInstance)
class ExtraProcessInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "bk_biz_id",
        "cluster_id",
        "bk_cloud_id",
        "ip",
        "listen_port",
        "proc_type",
    )
    search_fields = ("cluster_id", "ip", "bk_biz_id", "proc_type")


@admin.register(models.group.Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("bk_biz_id", "name")
    search_fields = ("name",)


@admin.register(models.group.GroupInstance)
class GroupInstanceAdmin(admin.ModelAdmin):
    list_display = ("group_id", "instance_id")
    search_fields = ("name",)


@admin.register(models.cluster_monitor.AppMonitorTopo)
class AppMonitorTopoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bk_biz_id",
        "db_type",
        "machine_type",
        "monitor_plugin",
        "monitor_plugin_id",
        "bk_set_id",
        "bk_set_name",
    )
    search_fields = (
        "bk_set_name",
        "bk_set_name",
    )
    list_filter = ("db_type", "machine_type")


@admin.register(models.cluster_monitor.ClusterMonitorTopo)
class ClusterMonitorTopoAdmin(admin.ModelAdmin):
    list_display = ("id", "bk_biz_id", "instance_id", "cluster_id", "bk_set_id", "bk_module_id", "machine_type")
    search_fields = (
        "cluster_id",
        "bk_module_id",
    )


@admin.register(models.cluster_monitor.SyncFailedMachine)
class SyncFailedMachineAdmin(admin.ModelAdmin):
    list_display = ("bk_host_id", "error")
    search_fields = ("error",)


@admin.register(models.tag.Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "bk_biz_id", "is_builtin", "type")
    search_fields = ("bk_biz_id", "key", "value")
