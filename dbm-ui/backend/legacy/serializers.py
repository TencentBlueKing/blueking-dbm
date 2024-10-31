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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.models import Cluster
from backend.exceptions import ValidationError


class CreateDNSSerializer(serializers.Serializer):
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
        domains = attrs.get("domains", [])
        domains = [domain["domain_name"] for domain in domains]
        if Cluster.objects.filter(immute_domain__in=domains).exists():
            raise ValidationError(_("域名存在于 DBM 中，不允许通过此接口修改，请联系管理员"))
        return attrs


class DeleteDNSSerializer(CreateDNSSerializer):
    class DeleteDomainSerializer(CreateDNSSerializer.CreateDomainSerializer):
        instances = serializers.ListField(
            help_text=_("实例列表"), child=serializers.IntegerField(), allow_empty=True, required=False, default=[]
        )

    domains = serializers.ListField(help_text=_("域名列表"), child=DeleteDomainSerializer(), allow_empty=False)
