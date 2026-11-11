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

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.db_meta.models import Cluster
from backend.db_services.dns_domain.format import format_managers
from backend.exceptions import ValidationError


class DBMDomainProtectMixin:
    @staticmethod
    def validate_domains_not_in_dbm(domain_names):
        # DNS 侧的域名允许以 "." 结尾，DBM 中存储的域名无结尾点
        domains = [domain_name.rstrip(".") for domain_name in domain_names]
        if Cluster.objects.filter(immute_domain__in=domains).exists():
            raise ValidationError(_("域名存在于 DBM 中，不允许通过此接口修改，请联系管理员"))


class CreateDNSSerializer(DBMDomainProtectMixin, serializers.Serializer):
    class CreateDomainSerializer(serializers.Serializer):
        domain_name = serializers.CharField(help_text=_("域名"))
        instances = serializers.ListField(help_text=_("实例列表"), child=serializers.CharField(), allow_empty=False)
        manager = serializers.CharField(help_text=_("管理者"), required=False, allow_blank=True)
        remark = serializers.CharField(help_text=_("域名备注信息"), required=False, allow_blank=True)
        domain_type = serializers.CharField(help_text=_("维护方式：0 集群托管，1 自主维护"), required=False, allow_blank=True)
        extends = serializers.CharField(help_text=_("域名自定义扩展字段"), required=False, allow_blank=True)

    app = serializers.CharField(help_text=_("GCS业务英文缩写"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    domains = serializers.ListField(help_text=_("域名列表"), child=CreateDomainSerializer(), allow_empty=False)

    def validate(self, attrs):
        domain_names = [domain["domain_name"] for domain in attrs.get("domains", [])]
        self.validate_domains_not_in_dbm(domain_names)
        for domain in attrs.get("domains", []):
            self._normalize_domain_type(domain)
        return attrs

    @staticmethod
    def _normalize_domain_type(domain):
        if "domain_type" not in domain:
            return
        raw = domain.get("domain_type")
        if raw in (None, "", "db"):
            domain.pop("domain_type", None)
            return
        try:
            domain["domain_type"] = int(raw)
        except (TypeError, ValueError):
            raise ValidationError(_("domain_type 必须是整数，0 表示集群托管，1 表示自主维护"))


class DeleteDNSSerializer(CreateDNSSerializer):
    class DeleteDomainSerializer(CreateDNSSerializer.CreateDomainSerializer):
        instances = serializers.ListField(
            help_text=_("实例列表"), child=serializers.CharField(), allow_empty=True, required=False, default=[]
        )

    operator = serializers.CharField(help_text=_("操作人，记为域名更新人；不传记为 system"), required=False, allow_blank=True)
    domains = serializers.ListField(help_text=_("域名列表"), child=DeleteDomainSerializer(), allow_empty=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not (attrs.get("operator") or "").strip():
            attrs.pop("operator", None)
        return attrs


class QueryDNSSerializer(serializers.Serializer):
    app = serializers.CharField(help_text=_("GCS业务英文缩写"), required=False, allow_blank=True)
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    domain_name = serializers.ListField(help_text=_("域名列表"), child=serializers.CharField(), required=False)
    ip = serializers.ListField(help_text=_("IP 列表"), child=serializers.CharField(), required=False)
    domain_type = serializers.ListField(help_text=_("域名类型列表"), child=serializers.CharField(), required=False)
    columns = serializers.ListField(help_text=_("返回数据列列表"), child=serializers.CharField(), allow_empty=False)

    def validate(self, attrs):
        if not attrs.get("domain_name") and not attrs.get("ip"):
            raise ValidationError(_("domain_name 与 ip 不能同时为空，请至少指定一个查询条件"))
        return attrs


class UpdateDNSSerializer(DBMDomainProtectMixin, serializers.Serializer):
    class UpdateDomainSetSerializer(serializers.Serializer):
        instance = serializers.CharField(help_text=_("新的实例，格式：ip#port"))

    app = serializers.CharField(help_text=_("GCS业务英文缩写"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    domain_name = serializers.CharField(help_text=_("域名"))
    instance = serializers.CharField(help_text=_("当前实例，格式：ip#port"))
    set = UpdateDomainSetSerializer(help_text=_("待修改的内容"))
    operator = serializers.CharField(help_text=_("操作人，记为更新人；不传记为 system"), required=False, allow_blank=True)
    manager = serializers.CharField(help_text=_("域名管理人，整体替换；不传则不变"), required=False, allow_blank=True)

    def validate(self, attrs):
        self.validate_domains_not_in_dbm([attrs["domain_name"]])
        if not (attrs.get("operator") or "").strip():
            attrs.pop("operator", None)
        if "manager" in attrs:
            raw = attrs.get("manager")
            manager = format_managers([raw])
            if raw not in (None, "") and not manager:
                raise ValidationError(_("manager 需要至少一个有效管理人"))
            if not manager:
                attrs.pop("manager", None)
            else:
                attrs["manager"] = manager
        return attrs
