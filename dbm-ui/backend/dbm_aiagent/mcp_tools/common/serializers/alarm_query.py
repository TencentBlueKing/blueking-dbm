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

from backend.db_monitor.constants import AlertLevelEnum, AlertStatusEnum


class AlertTagsSerializer(serializers.Serializer):
    key = serializers.CharField(help_text=_("标签名称"))
    value = serializers.CharField(help_text=_("标签值"))


class AlertInfoSerializer(serializers.Serializer):
    alert_id = serializers.CharField(help_text=_("告警记录Id"))
    alert_name = serializers.CharField(help_text=_("告警记录名称"))
    alert_status = serializers.ChoiceField(help_text=_("告警记录状态"), choices=AlertStatusEnum.get_choices())
    alert_severity = serializers.ChoiceField(help_text=_("告警级别"), choices=AlertLevelEnum.get_choices())
    alert_create_time = serializers.IntegerField(help_text=_("告警记录创建时间戳"))
    tags = serializers.ListField(child=AlertTagsSerializer(), help_text=_("告警记录的标签信息"))


class SearchAlertInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务Id"))
    cluster_domains = serializers.ListField(child=serializers.CharField(), help_text=_("待查询的集群域名列表"))
    start_time = serializers.DateTimeField(help_text=_("查询的起始时间"))
    end_time = serializers.DateTimeField(help_text=_("查询的截止时间"))


class SearchAlertOutputSerializer(serializers.Serializer):
    alert_infos = serializers.ListField(child=AlertInfoSerializer(), help_text=_("告警记录信息"))
