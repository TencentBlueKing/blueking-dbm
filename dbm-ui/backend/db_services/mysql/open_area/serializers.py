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

import itertools

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.bk_web.serializers import AuditedSerializer
from backend.db_meta.models import Cluster
from backend.db_services.mysql.open_area import mock_data
from backend.db_services.mysql.open_area.handlers import OpenAreaHandler
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig


class TendbOpenAreaSubConfigSerializer(serializers.Serializer):
    source_db = serializers.CharField(help_text=_("获取库表结构的源db"))
    # json字段，直接存储待克隆表结构列表，克隆所有表时为空列表
    schema_tblist = serializers.JSONField(help_text=_("获取表结构的源tb列表"), default=list)
    data_tblist = serializers.JSONField(help_text=_("获取表数据的源tb列表"), default=list)
    target_db_pattern = serializers.CharField(help_text=_("目标db范式"))
    # json字段，存储权限模板列表
    priv_data = serializers.JSONField(help_text=_("权限关联模板数据"), default=list)


class TendbOpenAreaConfigSerializer(AuditedSerializer, serializers.ModelSerializer):
    config_rules = serializers.ListSerializer(child=TendbOpenAreaSubConfigSerializer(), help_text=_("模板克隆规则列表"))

    class Meta:
        model = TendbOpenAreaConfig
        exclude = ("related_authorize",)
        swagger_schema_fields = {"example": mock_data.OPENAREA_TEMPLATE_DATA}

    def validate(self, attrs):
        # 校验集群是否存在
        if not Cluster.objects.filter(id=attrs["source_cluster_id"]).exists():
            raise serializers.ValidationError(_("源集群不存在，请选择合法集群"))

        # 校验分区名称是否唯一
        if not OpenAreaHandler.validate_only_openarea(
            bk_biz_id=attrs["bk_biz_id"], config_name=attrs["config_name"], config_id=getattr(self.instance, "id", 0)
        ):
            raise serializers.ValidationError(_("请保证同一业务下的开区模板命名不重复"))

        # (产品暂定)校验模板克隆规则的克隆DB不要重复
        source_dbs = [info["source_db"] for info in attrs["config_rules"]]
        if len(set(source_dbs)) != len(source_dbs):
            raise serializers.ValidationError(_("请保证校验模板克隆规则的克隆DB不要重复"))

        return attrs

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data["related_authorize"] = list(set(itertools.chain(*[_data["priv_data"] for _data in data["config_rules"]])))
        return data


class TendbOpenAreaResultPreviewSerializer(serializers.Serializer):
    class ConfigDataSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("目标集群"))
        vars = serializers.JSONField(help_text=_("变量表"))
        authorize_ips = serializers.JSONField(help_text=_("授权IP"))

    config_id = serializers.IntegerField(help_text=_("开区模板ID"))
    config_data = serializers.ListSerializer(help_text=_("开区数据列表"), child=ConfigDataSerializer())


class TendbOpenAreaResultPreviewResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.OPENAREA_PREVIEW_DATA}
