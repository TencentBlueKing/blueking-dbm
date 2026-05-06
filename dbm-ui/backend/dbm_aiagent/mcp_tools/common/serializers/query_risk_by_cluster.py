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


class QueryRiskByClusterInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domain = serializers.CharField(help_text=_("集群域名（单个）"))


class RiskMemoItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text=_("风险 ID"))
    name = serializers.CharField(help_text=_("风险名称"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    level = serializers.CharField(help_text=_("风险等级"))
    status = serializers.CharField(help_text=_("风险状态"))
    db_type = serializers.CharField(help_text=_("影响 DB 类型"))
    description = serializers.CharField(help_text=_("风险描述"))
    biz_inpact = serializers.CharField(help_text=_("业务影响"))
    is_special = serializers.BooleanField(help_text=_("是否特殊"))
    creator = serializers.CharField(help_text=_("创建人"))
    create_at = serializers.DateTimeField(help_text=_("创建时间"))


class QueryRiskByClusterOutputSerializer(serializers.Serializer):
    risks = serializers.ListSerializer(child=RiskMemoItemSerializer(), help_text=_("风险备忘录列表"))
