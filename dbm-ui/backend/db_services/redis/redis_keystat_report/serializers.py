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

from backend.db_services.redis.redis_keystat_report.models import RankItem, ReportItem, ReportRecord


class KeyStatReportRecordsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportRecord
        fields = "__all__"

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     # 处理 source_addr_list
    #     representation["source_addr_list"] = [item["addr"] for item in representation.get("source_addr_list", [])]
    #     return representation


class ReportItemDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItem
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["mem_used"] = f'{representation["mem_used_bytes"]}({representation["mem_used_pct"]})'
        return representation


class KeyStatRecordDetailSerializer(serializers.Serializer):
    record_id = serializers.IntegerField(help_text=_("记录id"))


class ExportKeyStatDetailSerializer(serializers.Serializer):
    record_ids = serializers.CharField(help_text=_("记录ID列表(多个用逗号分隔)"))


class RankItemDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RankItem
        fields = "__all__"


class KeyStatInstanceInfoSerializer(serializers.Serializer):
    instances = serializers.CharField(help_text=_("内存分析实例(多个实例用|连接)"))
