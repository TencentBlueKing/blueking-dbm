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

from django.utils.translation import ugettext as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.ticket.builders.mysql.mysql_partition import PartitionObjectSerializer

from ...ticket.builders.common.field import DBTimezoneField
from ...ticket.builders.mysql.base import DBTableField
from . import mock


class PartitionListSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    immute_domains = serializers.CharField(help_text=_("集群域名"), required=False)
    dblikes = serializers.CharField(help_text=_("匹配库"), required=False)
    tblikes = serializers.CharField(help_text=_("匹配表"), required=False)

    limit = serializers.IntegerField(required=False, default=10)
    offset = serializers.IntegerField(required=False, default=0)

    def validate(self, attrs):
        filter_fields = ["immute_domains", "dblikes", "tblikes"]
        for field in filter_fields:
            if field in attrs:
                attrs[field] = attrs[field].split(",")

        return attrs


class PartitionListResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_LIST_DATA}


class PartitionDeleteSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    ids = serializers.ListField(help_text=_("分区策略ID"), child=serializers.IntegerField())


class PartitionCreateSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    dblikes = serializers.ListField(help_text=_("匹配库列表(支持通配)"), child=DBTableField(db_field=True))
    tblikes = serializers.ListField(help_text=_("匹配表列表(不支持通配)"), child=DBTableField())
    partition_column = serializers.CharField(help_text=_("分区字段"))
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"))
    expire_time = serializers.IntegerField(help_text=_("过期时间"))
    partition_time_interval = serializers.IntegerField(help_text=_("分区间隔"))

    def validate(self, attrs):
        # 表不支持通配
        for tb in attrs["tblikes"]:
            if "%" in tb or "*" in tb:
                raise serializers.ValidationError(_("分区表不支持通配"))

        # 校验过期时间>=分区间隔，且为整数倍
        if attrs["expire_time"] and attrs["expire_time"] % attrs["partition_time_interval"]:
            raise serializers.ValidationError(_("过期时间大于等于分区间隔，且为分区间隔的整数倍"))

        # 补充集群信息
        cluster = Cluster.objects.get(id=attrs["cluster_id"])
        attrs.update(
            bk_biz_id=cluster.bk_biz_id,
            bk_cloud_id=cluster.bk_cloud_id,
            cluster_type=cluster.cluster_type,
            immute_domain=cluster.immute_domain,
            port=cluster.get_partition_port(),
            time_zone=cluster.time_zone,
            creator=self.context["request"].user.username,
            updator=self.context["request"].user.username,
        )

        return attrs


class PartitionUpdateSerializer(PartitionCreateSerializer):
    pass


class PartitionDisableSerializer(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    operator = serializers.SerializerMethodField(help_text=_("操作者"))
    ids = serializers.ListField(help_text=_("分区策略ID"), child=serializers.IntegerField())

    def get_operator(self, obj):
        return self.context["request"].user.username


class PartitionEnableSerializer(PartitionDisableSerializer):
    pass


class PartitionLogSerializer(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    config_id = serializers.IntegerField(help_text=_("分区策略ID"))
    start_time = DBTimezoneField(help_text=_("开始时间"), required=False)
    end_time = DBTimezoneField(help_text=_("结束时间"), required=False)

    limit = serializers.IntegerField(required=False, default=10)
    offset = serializers.IntegerField(required=False, default=0)


class PartitionLogResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_LOG_DATA}


class PartitionDryRunSerializer(serializers.Serializer):
    config_id = serializers.IntegerField(help_text=_("分区配置ID"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    port = serializers.SerializerMethodField(help_text=_("PORT"))

    def get_port(self, obj):
        return Cluster.objects.get(id=obj["cluster_id"]).get_partition_port()


class PartitionDryRunResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_DRY_RUN_DATA}


class PartitionRunSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    partition_objects = serializers.DictField(
        help_text=_("分区执行对象列表"), child=serializers.ListSerializer(child=PartitionObjectSerializer())
    )


class PartitionColumnVerifySerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("云区域ID"))
    dblikes = serializers.ListField(help_text=_("匹配库列表(支持通配)"), child=DBTableField(db_field=True))
    tblikes = serializers.ListField(help_text=_("匹配表列表(不支持通配)"), child=DBTableField())
    partition_column = serializers.CharField(help_text=_("分区字段"))
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"))

    def validate(self, attrs):
        return attrs


class PartitionColumnVerifyResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_FIELD_VERIFY_DATA}
