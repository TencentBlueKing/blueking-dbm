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
from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models.system import SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_services.cmdb.biz import list_modules_by_biz
from backend.exceptions import ValidationError
from backend.ticket.builders import BuilderFactory
from backend.ticket.contexts import TicketContext


class MysqlHaApplyQuickMinorPassSerializer(serializers.Serializer):
    class DetailSerializer(serializers.Serializer):
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))
        city_code = serializers.CharField(help_text=_("业务ID"))
        domain_key = serializers.CharField(help_text=_("域名关键字"))

    remark = serializers.CharField(help_text=_("备注"), required=False, default="", allow_blank=True, allow_null=True)
    ticket_type = serializers.CharField(help_text=_("单据类型"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    details = DetailSerializer(help_text=_("单据详情信息"))

    def get_exact_serializer(self, ticket_type: Optional[str] = None):
        if not ticket_type:
            return serializers.Serializer()
        slz = BuilderFactory.get_serializer(ticket_type)

        # 更新上下文信息
        slz.context.update(self.context)
        slz.context.update({"ticket_type": ticket_type})
        slz.context.update({"bk_biz_id": self.context["request"].data.get("bk_biz_id")})
        slz.context.update({"ticket_ctx": TicketContext()})
        return slz

    def get_context_ticket_type(self):
        return self.context["request"].data["ticket_type"]

    def get_version(self, bk_biz_id, db_module_id):
        list_modules = list_modules_by_biz(bk_biz_id, ClusterType.TenDBHA.value)
        for module in list_modules:
            if db_module_id == module["db_module_id"]:
                conf_items = module["db_module_info"]["conf_items"]
                return [conf["conf_value"] for conf in conf_items if conf["conf_name"] == "db_version"][0]

    def validate(self, attrs):
        ticket_type = self.get_context_ticket_type()
        resource_specs = SystemSettings.get_setting_value(key=SystemSettingsEnum.QUICK_MINOR_POAA.value)
        resource_spec = resource_specs.pop("mysql")
        version_list = resource_spec["backend_group"].pop("version")
        version = self.get_version(attrs["bk_biz_id"], attrs["details"]["db_module_id"])
        if version not in version_list:
            raise ValidationError(_("要部署的集群版本: {}不在配置版本中: {}".format(version, version_list)))
        extra_info = {"location_spec": {"city": attrs["details"]["city_code"]}}
        resource_spec["backend_group"].update(extra_info)
        resource_spec["proxy"].update(extra_info)
        attrs["details"]["spec"] = ""
        attrs["details"]["cluster_count"] = 1
        attrs["details"]["inst_num"] = 1
        attrs["details"]["ip_source"] = "resource_pool"
        attrs["details"]["domains"] = [{"key": attrs["details"].pop("domain_key")}]
        attrs["details"]["resource_spec"] = resource_spec
        return self.get_exact_serializer(ticket_type).validate(attrs["details"])
