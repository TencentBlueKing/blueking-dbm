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
import operator
from functools import reduce

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import StorageInstance
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBInstanceReloadDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class InstanceReloadDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_host_id = serializers.IntegerField(help_text=_("实例主机ID"))
        port = serializers.IntegerField(help_text=_("实例Port"))
        role = serializers.CharField(help_text=_("角色"), required=False)

    infos = serializers.ListSerializer(help_text=_("重启信息"), child=InstanceReloadDetailSerializer())

    def validate(self, attrs):
        return attrs


class MongoDBInstanceReloadFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.instance_restart

    def format_ticket_data(self):
        # 查询重启的实例
        storage_filters = reduce(
            operator.or_, [Q(machine=info["bk_host_id"], port=info["port"]) for info in self.ticket_data["infos"]]
        )
        storages_map = {
            f"{storage.machine.bk_host_id}:{storage.port}": storage
            for storage in StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(storage_filters)
        }
        # 补充重启的角色信息
        for info in self.ticket_data["infos"]:
            storage = storages_map[f"{info['bk_host_id']}:{info['port']}"]
            info.update(
                role=storage.machine_type,
                ip=storage.machine.ip,
                bk_cloud_id=storage.cluster.first().bk_cloud_id,
                db_version=storage.cluster.first().major_version,
            )


@builders.BuilderFactory.register(TicketType.MONGODB_INSTANCE_RELOAD)
class MongoDBInstanceReloadApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBInstanceReloadDetailSerializer
    inner_flow_builder = MongoDBInstanceReloadFlowParamBuilder
    inner_flow_name = _("MongoDB 实例重启")

    def patch_ticket_detail(self):
        for info in self.ticket.details["infos"]:
            info["instance_id"] = f"{info['bk_host_id']}:{info['port']}"
        self.ticket.save(update_fields=["details"])
