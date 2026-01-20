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

from backend.constants import IP_PORT_DIVIDER
from backend.db_services.dbbase.instances.handlers import InstanceHandler
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
        dry_run = serializers.BooleanField(help_text=_("是否演练"), default=False)
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
        instance_address = serializers.CharField(help_text=_("实例地址"), required=False)
        master_domain = serializers.CharField(help_text=_("集群域名"), required=False)

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

    def patch_ticket_detail(self):
        """补充单据 infos 的展示字段：cluster_id/instance_address/master_domain"""
        infos = self.ticket.details.get("infos", [])
        if not infos:
            return

        query_instances = [
            f"{info['bk_cloud_id']}:{info['ip']}:{info['port']}"
            for info in infos
            if info.get("ip") and info.get("port")
        ]
        if not query_instances:
            return

        checked = InstanceHandler(bk_biz_id=self.ticket.bk_biz_id).check_instances(
            query_instances=query_instances,
            db_type="mongodb",
            cluster_type=[
                # 单据只允许 Mongo 的集群类型
                "MongoReplicaSet",
                "MongoShardedCluster",
            ],
        )

        # 建立 instance_address -> info 的映射
        addr__checked_map = {row.get("instance_address"): row for row in checked}

        for info in infos:
            instance_address = f"{info.get('ip')}{IP_PORT_DIVIDER}{info.get('port')}"
            matched = addr__checked_map.get(instance_address)
            if not matched:
                continue
            info.update(
                {
                    "cluster_id": matched.get("cluster_id"),
                    "instance_address": matched.get("instance_address"),
                    "master_domain": matched.get("master_domain"),
                }
            )
