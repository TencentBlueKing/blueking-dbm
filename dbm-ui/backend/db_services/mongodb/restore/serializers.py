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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_services.mongodb.restore import mock_data


class QueryBackupLogSerializer(serializers.Serializer):
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())

    def validate(self, attrs):
        if attrs["cluster_type"] == ClusterType.MongoShardedCluster and len(attrs["cluster_ids"]) > 1:
            raise serializers.ValidationError(_("分片集群只支持查询单个"))
        return attrs


class QueryBackupLogResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.CLUSTER_BACKUP_LOGS_DATA}


class QueryRestoreRecordSerializer(serializers.Serializer):
    limit = serializers.IntegerField(help_text=_("分页限制"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始"), required=False, default=0)
    immute_domain = serializers.CharField(help_text=_("集群域名"), required=False)
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), required=False, choices=ClusterType.get_choices())
    ips = serializers.CharField(help_text=_("过滤ip，多个ip以逗号分割"), required=False)

    def get_conditions(self, attr):
        filters = Q()
        if attr.get("cluster_type"):
            filters &= Q(cluster_type=attr["cluster_type"])
        if attr.get("immute_domain"):
            filters &= Q(immute_domain__icontains=attr["immute_domain"])
        if attr.get("ips"):
            ips = attr["ips"].split(",")
            filters &= Q(storageinstance__machine__ip__in=ips) | Q(proxyinstance__machine__ip__in=ips)

        return filters


class QueryRestoreRecordResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.RESTORE_RECORD_DATA}
