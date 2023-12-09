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

from backend.db_proxy.views import mock_data
from backend.db_proxy.views.serialiers import BaseProxyPassSerializer


class GetAllDomainListSerializer(BaseProxyPassSerializer):
    pass


class GetAllDomainListResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.GET_ALL_DOMAIN_LIST_DATA_RESPONSE}


class GetDomainSerializer(BaseProxyPassSerializer):
    app = serializers.CharField(help_text=_("GCS业务英文缩写"), required=False)
    domain_name = serializers.ListField(help_text=_("查询的域名列表"), child=serializers.CharField(), required=False)
    ip = serializers.ListField(help_text=_("查询的IP列表"), child=serializers.CharField(), required=False)
    columns = serializers.ListField(help_text=_("返回数据列表字段"), child=serializers.CharField(), required=False)


class GetDomainResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.GET_DOMAIN_DATA_RESPONSE}


class DeleteDomainSerializer(BaseProxyPassSerializer):
    class DomainSerializer(serializers.Serializer):
        domain_name = serializers.CharField(help_text=_("查询的域名"))
        instances = serializers.ListField(help_text=_("实例列表"), child=serializers.CharField(), required=False)

    app = serializers.CharField(help_text=_("GCS业务英文缩写"))
    domains = serializers.ListSerializer(help_text=_("域名列表"), child=DomainSerializer())


class DeleteDomainResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.DELETE_DOMAIN_DATA_RESPONSE}


class BatchPostDomainSerializer(BaseProxyPassSerializer):
    class BatchPostInstanceSetSerializer(serializers.Serializer):
        old_instance = serializers.CharField(help_text=_("旧实例节点"))
        new_instance = serializers.CharField(help_text=_("新实例节点"))

    app = serializers.CharField(help_text=_("GCS业务英文缩写"))
    domain_name = serializers.CharField(help_text=_("查询的域名"))
    sets = serializers.ListField(help_text=_("修改数组"), child=BatchPostInstanceSetSerializer())


class BatchPostDomainResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.BATCH_DELETE_DOMAIN_DATA_RESPONSE}


class PostDomainSerializer(BaseProxyPassSerializer):
    class PostInstanceSetSerializer(serializers.Serializer):
        instance = serializers.CharField(help_text=_("新的实例节点"))

    app = serializers.CharField(help_text=_("GCS业务英文缩写"))
    domain_name = serializers.CharField(help_text=_("查询的域名"))
    set = PostInstanceSetSerializer(help_text=_("修改列列表"))
    instance = serializers.CharField(help_text=_("实例节点"))


class PostDomainResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.POST_DOMAIN_DATA_RESPONSE}


class PutDomainSerializer(BaseProxyPassSerializer):
    class PutDomainDetailSerializer(serializers.Serializer):
        domain_name = serializers.CharField(help_text=_("查询的域名"))
        instances = serializers.ListField(help_text=_("实例列表"), child=serializers.CharField())
        manager = serializers.CharField(help_text=_("管理者"), required=False, default="DBA")
        remark = serializers.CharField(help_text=_("域名备注信息"), required=False, default="")
        domain_type = serializers.CharField(help_text=_("域名类型"), required=False, default="db")

    app = serializers.CharField(help_text=_("GCS业务英文缩写"))
    domains = serializers.ListSerializer(help_text=_("域名列表"), child=PutDomainDetailSerializer())


class PutDomainResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.PUT_DOMAIN_DATA_RESPONSE}
