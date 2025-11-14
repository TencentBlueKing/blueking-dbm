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
from rest_framework import serializers

from backend.db_services.redis.redis_keystat_report.models.redis_keystat_report import (
    ReportRecord,
    ReportItem,
    RankItem,
)


class CreateKeyStatReportRecordSerializer(serializers.ModelSerializer):
    creator = serializers.CharField(read_only=True)
    updater = serializers.CharField(read_only=True)

    class Meta:
        model = ReportRecord
        fields = "__all__"


class UpdateKeyStatReportRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportRecord
        fields = [
            "update_at",
            "status",
            "exec_ip",
            "keystat_report_rows_num",
            "keystat_rank_rows_num",
            "analysis_time",
            "redis_version",
            "source_type",
            "source_role",
            "source_addr_list",
            "atime_available",
            "analyzed_shard_num",
            "root_id",
        ]


class CreateKeyStatReportItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportItem
        # fields = "__all__"
        exclude = ["id"]


class CreateKeyStatRankItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RankItem
        # fields = "__all__"
        exclude = ["id"]
