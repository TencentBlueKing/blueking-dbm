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

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterPhase, ClusterType


class IsClusterDuplicatedSerializer(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    name = serializers.CharField(help_text=_("集群名"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class IsClusterDuplicatedResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"is_duplicated": True}}


class QueryAllTypeClusterSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_types = serializers.CharField(help_text=_("集群类型(逗号分隔)"), required=False)
    immute_domain = serializers.CharField(help_text=_("集群域名"), required=False)
    phase = serializers.ChoiceField(help_text=_("集群阶段状态"), required=False, choices=ClusterPhase.get_choices())

    def get_conditions(self, attr):
        conditions = {"bk_biz_id": attr["bk_biz_id"]}
        if attr.get("cluster_types"):
            conditions["cluster_type__in"] = attr["cluster_types"].split(",")
        if attr.get("immute_domain"):
            conditions["immute_domain__icontains"] = attr["immute_domain"]
        if attr.get("phase"):
            conditions["phase"] = attr["phase"]

        return conditions


class QueryAllTypeClusterResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": [{"id": 47, "immute_domain": "mysql.dba.db.com"}]}


class CommonQueryClusterSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_types = serializers.CharField(help_text=_("集群类型(逗号分隔)"))
    cluster_ids = serializers.CharField(help_text=_("集群ID(逗号分割)"), required=False, default="")

    def validate(self, attrs):
        attrs["cluster_types"] = attrs["cluster_types"].split(",")
        attrs["cluster_ids"] = attrs["cluster_ids"].split(",") if attrs["cluster_ids"] else []
        return attrs


class CommonQueryClusterResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": []}


class ClusterFilterSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    exact_domain = serializers.CharField(help_text=_("域名精确查询"), required=False)
    # 后续有其他过滤条件可以再加

    def validate(self, attrs):
        filters = Q(bk_biz_id=attrs["bk_biz_id"])
        filters &= Q(immute_domain=attrs["exact_domain"]) if attrs.get("exact_domain") else Q()
        attrs["filters"] = filters
        return attrs
