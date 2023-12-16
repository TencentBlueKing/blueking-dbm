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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, ClusterTypeMachineTypeDefine
from backend.db_meta.models import Cluster, Machine
from backend.flow.consts import MongoDBBackupFileTagEnum, MongoShardedClusterBackupType
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
    DBTableSerializer,
)
from backend.ticket.constants import TicketType


class MongoDBBackupDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class FullBackupDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        ns_filter = DBTableSerializer(help_text=_("库表选择器"))
        backup_host = serializers.CharField(help_text=_("备份节点"), required=False)
        backup_type = serializers.ChoiceField(
            help_text=_("备份方式"), choices=MongoShardedClusterBackupType.get_choices(), required=False
        )

    file_tag = serializers.ChoiceField(help_text=_("备份保存时间"), choices=MongoDBBackupFileTagEnum.get_choices())
    infos = serializers.ListSerializer(help_text=_("备份信息"), child=FullBackupDetailSerializer())

    def validate(self, attrs):
        backup_host_ips = [info["backup_host"] for info in attrs["infos"] if info.get("backup_host")]
        # 分片集的machine type包含了副本集的
        mongo_machine_types = ClusterTypeMachineTypeDefine[ClusterType.MongoShardedCluster]
        backup_real_ips = Machine.objects.filter(
            ip__in=backup_host_ips, machine_type__in=mongo_machine_types
        ).values_list("ip", flat=True)

        for info in attrs["infos"]:
            if info.get("backup_type") != MongoShardedClusterBackupType.MONGOS:
                continue
            # 校验备份方式是mongos，存在备份节点
            if not info.get("backup_host"):
                raise serializers.ValidationError(_("如果备份方式选择mongos，请输入备份节点"))
            # 校验备份节点的合法性
            if info["backup_host"] not in backup_real_ips:
                raise serializers.ValidationError(_("请保证备份节点{}是mongodb的机器").format(info["backup_host"]))

        return attrs


class MongoDBBackupFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    @classmethod
    def add_cluster_type_info(cls, ticket_data):
        cluster_ids = [info["cluster_id"] for info in ticket_data["infos"]]
        id__cluster = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for info in ticket_data["infos"]:
            info["cluster_type"] = id__cluster[info["cluster_id"]].cluster_type

    def format_ticket_data(self):
        self.add_cluster_type_info(self.ticket_data)


@builders.BuilderFactory.register(TicketType.MONGODB_BACKUP)
class MongoDBBackupApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBBackupDetailSerializer
    inner_flow_builder = MongoDBBackupFlowParamBuilder
    inner_flow_name = _("MongoDB 库表备份执行")
