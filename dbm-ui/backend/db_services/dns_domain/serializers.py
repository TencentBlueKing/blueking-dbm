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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_services.dns_domain.constants import AUDIT_SCOPE_DOMAIN, AUDIT_SCOPE_GLOBAL, AuditAction, MaintainType


class DnsDomainListSerializer(serializers.Serializer):
    domain = serializers.CharField(required=False, allow_blank=True, default="")
    maintain_type = serializers.ChoiceField(choices=MaintainType.get_choices(), required=False, allow_blank=True)
    owner = serializers.CharField(required=False, allow_blank=True, default="")
    mine = serializers.BooleanField(required=False, default=False)
    limit = serializers.IntegerField(required=False, default=20, min_value=-1)
    offset = serializers.IntegerField(required=False, default=0, min_value=0)


class DnsDomainDetailSerializer(serializers.Serializer):
    domain = serializers.CharField()


class DnsDomainCreateSerializer(serializers.Serializer):
    domain = serializers.CharField()
    ips = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    owners = serializers.ListField(child=serializers.CharField(), required=False)
    remark = serializers.CharField(required=False, allow_blank=True, default="")
    bk_cloud_id = serializers.IntegerField(required=False, min_value=0)


class DnsDomainUpdateSerializer(serializers.Serializer):
    domain = serializers.CharField()
    ips = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    owners = serializers.ListField(child=serializers.CharField(), allow_empty=False)
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class DnsDomainDeleteSerializer(serializers.Serializer):
    domain = serializers.CharField()
    confirm_domain = serializers.CharField(help_text=_("输入完整域名确认删除"))


class DnsDomainAuditSerializer(serializers.Serializer):
    scope = serializers.ChoiceField(choices=[(AUDIT_SCOPE_DOMAIN, _("本域")), (AUDIT_SCOPE_GLOBAL, _("全局"))])
    domain = serializers.CharField(required=False, allow_blank=True, default="")
    keyword = serializers.CharField(required=False, allow_blank=True, default="")
    operator = serializers.CharField(required=False, allow_blank=True, default="")
    action = serializers.ChoiceField(choices=AuditAction.get_choices(), required=False, allow_blank=True)
    limit = serializers.IntegerField(required=False, default=20, min_value=-1)
    offset = serializers.IntegerField(required=False, default=0, min_value=0)

    def validate(self, attrs):
        if attrs["scope"] == AUDIT_SCOPE_DOMAIN and not attrs.get("domain"):
            raise serializers.ValidationError(_("本域日志需要域名"))
        return attrs


class DnsDomainAuditExportSerializer(DnsDomainAuditSerializer):
    limit = serializers.IntegerField(required=False, default=-1)
    offset = serializers.IntegerField(required=False, default=0)
