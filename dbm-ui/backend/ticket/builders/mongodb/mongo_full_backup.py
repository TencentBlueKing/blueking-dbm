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

from backend.flow.consts import MongoDBBackupFileTagEnum
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.builders.mongodb.mongo_backup import MongoDBBackupFlowParamBuilder
from backend.ticket.constants import TicketType


class MongoDBFullBackupDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class FullBackupDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))

    oplog = serializers.BooleanField(help_text=_("是否需要oplog备份"))
    file_tag = serializers.ChoiceField(help_text=_("备份保存时间"), choices=MongoDBBackupFileTagEnum.get_choices())
    infos = serializers.ListSerializer(help_text=_("备份信息"), child=FullBackupDetailSerializer())

    def validate(self, attrs):
        return attrs


class MongoDBFullBackupFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.fake_scene

    def format_ticket_data(self):
        MongoDBBackupFlowParamBuilder.add_cluster_type_info(self.ticket_data)


@builders.BuilderFactory.register(TicketType.MONGODB_FULL_BACKUP)
class MongoDBClearApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBFullBackupDetailSerializer
    inner_flow_builder = MongoDBFullBackupFlowParamBuilder
    inner_flow_name = _("MongoDB 全库备份执行")
