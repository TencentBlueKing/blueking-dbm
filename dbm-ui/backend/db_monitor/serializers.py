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

from backend.bk_web.serializers import AuditedSerializer
from backend.db_meta.enums import ClusterType
from backend.db_monitor.models import CollectTemplate, RuleTemplate


class GetDashboardSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=True)
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices(), required=True)
    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    instance_id = serializers.IntegerField(help_text=_("节点实例ID"), required=False)


class DashboardUrlSerializer(serializers.Serializer):
    url = serializers.URLField(help_text=_("监控仪表盘地址"))


class CollectTemplateSerializer(AuditedSerializer, serializers.ModelSerializer):
    class Meta:
        model = CollectTemplate
        fields = "__all__"


class RuleTemplateSerializer(AuditedSerializer, serializers.ModelSerializer):
    class Meta:
        model = RuleTemplate
        fields = "__all__"
