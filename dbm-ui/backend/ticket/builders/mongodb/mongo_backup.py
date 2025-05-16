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

from backend.db_meta.enums import ClusterType
from backend.flow.consts import MongoDBBackupFileTagEnum
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
    BaseMongoOperateFlowParamBuilder,
    DBTableSerializer,
)
from backend.ticket.constants import TicketType


class MongoDBBackupDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class FullBackupDetailSerializer(serializers.Serializer):
        ns_filter = DBTableSerializer(help_text=_("库表选择器"))
        cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices(), required=False)
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(help_text=_("集群ID")))

    file_tag = serializers.ChoiceField(help_text=_("备份保存时间"), choices=MongoDBBackupFileTagEnum.get_choices())
    infos = serializers.ListSerializer(help_text=_("备份信息"), child=FullBackupDetailSerializer())


class MongoDBBackupFlowParamBuilder(BaseMongoOperateFlowParamBuilder):
    controller = MongoDBController.mongo_backup

    def format_ticket_data(self):
        self.ticket_data["oplog"] = False
        self.ticket_data["infos"] = self.scatter_cluster_id_info(self.ticket_data["infos"])
        self.ticket_data["infos"] = self.add_cluster_type_info(self.ticket_data["infos"])


@builders.BuilderFactory.register(TicketType.MONGODB_BACKUP)
class MongoDBBackupApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBBackupDetailSerializer
    inner_flow_builder = MongoDBBackupFlowParamBuilder
    inner_flow_name = _("MongoDB 库表备份执行")
