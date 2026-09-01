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
        domain_type = serializers.CharField(help_text=_("域名类型"), required=False, allow_blank=True)
        extends = serializers.CharField(help_text=_("域名自定义扩展字段"), required=False, allow_blank=True)

    app = serializers.CharField(help_text=_("GCS业务英文缩写"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域 ID"))
    domains = serializers.ListField(help_text=_("域名列表"), child=CreateDomainSerializer(), allow_empty=False)

    def validate(self, attrs):
        domain_names = [domain["domain_name"] for domain in attrs.get("domains", [])]
        self.validate_domains_not_in_dbm(domain_names)
        return attrs


class DeleteDNSSerializer(CreateDNSSerializer):
    class DeleteDomainSerializer(CreateDNSSerializer.CreateDomainSerializer):
        instances = serializers.ListField(
            help_text=_("实例列表"), child=serializers.CharField(), allow_empty=True, required=False, default=[]
        )

    domains = serializers.ListField(help_text=_("域名列表"), child=DeleteDomainSerializer(), allow_empty=False)


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

    def validate(self, attrs):
        self.validate_domains_not_in_dbm([attrs["domain_name"]])
        return attrs
