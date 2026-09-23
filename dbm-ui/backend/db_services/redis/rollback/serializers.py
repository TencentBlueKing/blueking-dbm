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
from datetime import timedelta

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.bk_web.serializers import AuditedSerializer
from backend.db_services.redis.rollback.constants import BACKUP_BATCH_MAX_WINDOW_DAYS
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.ticket.builders.common.field import DBTimezoneField
from backend.utils.time import str2datetime


class RollbackSerializer(AuditedSerializer, serializers.ModelSerializer):
    """redis构造实例记录序列化"""

    specification = serializers.JSONField()
    prod_instance_range = serializers.JSONField()
    temp_instance_range = serializers.JSONField()
    prod_temp_instance_pairs = serializers.JSONField()

    class Meta:
        model = TbTendisRollbackTasks
        exclude = (
            "temp_proxy_password",
            "status",
        )


class BackupBatchQuerySerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    start_time = DBTimezoneField(help_text=_("开始时间"), required=False, allow_null=True, allow_blank=True)
    end_time = DBTimezoneField(help_text=_("结束时间"), required=False, allow_null=True, allow_blank=True)
    shard_values = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True, help_text=_("按分片过滤，不传表示全部")
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start_time, end_time = attrs.get("start_time"), attrs.get("end_time")
        if not start_time and not end_time:
            return attrs
        if not (start_time and end_time):
            raise serializers.ValidationError(_("start_time 与 end_time 必须成对提供"))
        start, end = str2datetime(start_time), str2datetime(end_time)
        if start > end:
            raise serializers.ValidationError(_("start_time 不能晚于 end_time"))
        span = end - start
        if span > timedelta(days=BACKUP_BATCH_MAX_WINDOW_DAYS):
            raise serializers.ValidationError(
                _("备份批次查询跨度不能超过 {} 天，当前 {} 天").format(BACKUP_BATCH_MAX_WINDOW_DAYS, span.days)
            )
        return attrs


class BatchDetailQuerySerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    backup_identify = serializers.CharField(help_text=_("备份批次"))
    shard_values = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True, help_text=_("按分片过滤，不传表示该批次全部分片")
    )


class ShardSelectionSerializer(serializers.Serializer):
    shard_value = serializers.CharField(help_text=_("该批次当时的分片"))
    round_key = serializers.CharField(help_text=_("轮次"), required=False, allow_blank=True, default="")


class RollbackPrecheckSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    backup_identify = serializers.CharField(help_text=_("备份批次"), required=True)
    shards = serializers.ListField(
        help_text=_("勾选的分片与轮次，为空表示该批次全部分片取最新一轮"),
        child=ShardSelectionSerializer(),
        required=False,
        allow_empty=True,
    )
    key_white_regex = serializers.CharField(required=False, allow_blank=True, default="")
    key_black_regex = serializers.CharField(required=False, allow_blank=True, default="")
    resource_spec = serializers.JSONField(required=False)


class CheckTimeSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群id"))
    master_instances = serializers.ListField(help_text=_("master实例列表"))
    rollback_time = DBTimezoneField(help_text=_("构造时间"))

    class Meta:
        swagger_schema_fields = {
            "example": {
                "cluster_id": 1,
                "master_instances": ["127.0.0.1:30004", "127.0.0.1:30005"],
                "rollback_time": "2023-12-15 04:15:55.860498+00:00",
            }
        }
