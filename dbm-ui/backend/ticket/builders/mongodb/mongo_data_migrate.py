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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.flow.utils.mongodb.version_utils import compare_mongodb_versions
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
    BaseMongoOperateFlowParamBuilder,
    DBTableSerializer,
)
from backend.ticket.constants import TicketType

SOURCE_BACKUP_TICKET = "backup_ticket"
SOURCE_CLUSTER = "cluster"
_MIGRATE_CLUSTER_TYPES = (
    ClusterType.MongoReplicaSet.value,
    ClusterType.MongoShardedCluster.value,
)


class MongoDBDataMigrateDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class DataMigrateDetailSerializer(serializers.Serializer):
        source_mode = serializers.ChoiceField(help_text=_("数据源模式"), choices=[SOURCE_BACKUP_TICKET, SOURCE_CLUSTER])
        source_cluster_id = serializers.IntegerField(help_text=_("源集群ID"))
        target_cluster_id = serializers.IntegerField(help_text=_("目标集群ID"))
        backup_ticket_id = serializers.IntegerField(help_text=_("备份单据ID"), required=False, allow_null=True)
        ns_filter = DBTableSerializer(help_text=_("库表选择器"), required=False, allow_null=True)
        require_target_sharded = serializers.BooleanField(
            help_text=_("目标为分片时是否强制检查已 shardCollection，默认否"),
            required=False,
            default=False,
        )

        def validate(self, attrs):
            if attrs["source_mode"] == SOURCE_BACKUP_TICKET and not attrs.get("backup_ticket_id"):
                raise serializers.ValidationError(_("backup_ticket 模式必须提供 backup_ticket_id"))
            if attrs["source_cluster_id"] == attrs["target_cluster_id"]:
                raise serializers.ValidationError(_("源集群和目标集群不能相同"))
            return attrs

    infos = serializers.ListSerializer(help_text=_("数据迁移信息"), child=DataMigrateDetailSerializer())

    def validate(self, attrs):
        attrs = super().validate(attrs)
        cluster_ids = set()
        for info in attrs["infos"]:
            cluster_ids.add(info["source_cluster_id"])
            cluster_ids.add(info["target_cluster_id"])
        clusters = {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)}
        missing = cluster_ids - set(clusters)
        if missing:
            raise serializers.ValidationError(_("集群不存在: {}").format(",".join(map(str, missing))))
        for info in attrs["infos"]:
            src = clusters[info["source_cluster_id"]]
            dst = clusters[info["target_cluster_id"]]
            if src.cluster_type not in _MIGRATE_CLUSTER_TYPES or dst.cluster_type not in _MIGRATE_CLUSTER_TYPES:
                raise serializers.ValidationError(
                    _("仅支持副本集与分片集群互迁: {} -> {}").format(src.cluster_type, dst.cluster_type)
                )
            try:
                if compare_mongodb_versions(dst.major_version, src.major_version) < 0:
                    raise serializers.ValidationError(
                        _("目标版本 {} 低于源版本 {}").format(dst.major_version, src.major_version)
                    )
            except ValueError as err:
                raise serializers.ValidationError(_("major_version 无效: {}").format(err))
            if src.bk_cloud_id != dst.bk_cloud_id:
                raise serializers.ValidationError(_("源与目标云区域不一致: {} vs {}").format(src.bk_cloud_id, dst.bk_cloud_id))
        return attrs


class MongoDBDataMigrateFlowParamBuilder(BaseMongoOperateFlowParamBuilder):
    controller = MongoDBController.mongo_data_migrate


@builders.BuilderFactory.register(TicketType.MONGODB_DATA_MIGRATE)
class MongoDBDataMigrateFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBDataMigrateDetailSerializer
    inner_flow_builder = MongoDBDataMigrateFlowParamBuilder
    inner_flow_name = _("MongoDB 数据迁移执行")
