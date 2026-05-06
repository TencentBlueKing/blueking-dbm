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

from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBInstanceFixStatusDetailSerializer(BaseMongoDBOperateDetailSerializer):
    """MongoDB Mongos/instance 状态修复单据参数"""

    class InstanceFixStatusInfoSerializer(serializers.Serializer):
        ip = serializers.IPAddressField(help_text=_("Mongos/instance IP"))
        port = serializers.IntegerField(help_text=_("Mongos/instance 端口"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        dry_run = serializers.BooleanField(help_text=_("是否测试"), default=False)
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=True)
        instance_address = serializers.CharField(help_text=_("实例地址"), required=True)
        master_domain = serializers.CharField(help_text=_("集群域名"), required=True)

    infos = serializers.ListSerializer(
        help_text=_("Mongos/instance 状态修复信息"), child=InstanceFixStatusInfoSerializer(), allow_empty=False
    )


class MongoDBInstanceFixStatusFlowParamBuilder(builders.FlowParamBuilder):
    """构建 MongoDB Mongos/instance 状态修复 Flow 参数，并指定 controller"""

    controller = MongoDBController.instance_fix_status


@builders.BuilderFactory.register(TicketType.MONGODB_INSTANCE_FIX_STATUS, is_apply=False)
class MongoDBInstanceFixStatusFlowBuilder(BaseMongoDBTicketFlowBuilder):
    """MongoDB Mongos/instance 状态修复单据 Flow 构建器"""

    serializer = MongoDBInstanceFixStatusDetailSerializer
    inner_flow_builder = MongoDBInstanceFixStatusFlowParamBuilder
    inner_flow_name = _("MongoDB Mongos/instance 状态修复")

    # 需要审批和人工确认
    default_need_itsm = True
    default_need_manual_confirm = True
