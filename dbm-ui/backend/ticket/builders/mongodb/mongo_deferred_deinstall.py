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

from backend.db_meta.models import AppCache, Machine
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBOperateResourceParamBuilder,
    BaseMongoShardedTicketFlowBuilder,
)
from backend.ticket.constants import TicketType


class MongoDBDeferredDeInstallDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class InstanceInfoSerializer(serializers.Serializer):
        ip = serializers.CharField(help_text=_("IP地址"))
        port = serializers.IntegerField(help_text=_("端口"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云ID"))
        role = serializers.CharField(help_text=_("实例角色 mongod/mongos"), required=False, allow_blank=True)
        instance_type = serializers.CharField(help_text=_("实例类型 mongod/mongos"), required=False, allow_blank=True)
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
        set_id = serializers.CharField(help_text=_("副本集/分片名"), required=False, allow_blank=True)

    infos = serializers.ListSerializer(help_text=_("延迟下架实例列表"), child=InstanceInfoSerializer())
    poll_interval_sec = serializers.IntegerField(help_text=_("GSE 轮询间隔秒"), required=False, default=300)
    max_wait_hours = serializers.IntegerField(help_text=_("最长等待小时"), required=False, default=168)


class MongoDBDeferredDeInstallFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.deferred_deinstall

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


class MongoDBDeferredDeInstallResourceParamBuilder(BaseMongoDBOperateResourceParamBuilder):
    def format(self):
        pass

    def post_callback(self):
        pass


@builders.BuilderFactory.register(
    TicketType.MONGODB_DEFERRED_DEINSTALL, is_apply=True, is_recycle=True, iam=ActionEnum.MONGODB_MANAGE
)
class MongoDBDeferredDeInstallFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoDBDeferredDeInstallDetailSerializer
    inner_flow_builder = MongoDBDeferredDeInstallFlowParamBuilder
    inner_flow_name = _("MongoDB 延迟下架")
    resource_batch_apply_builder = MongoDBDeferredDeInstallResourceParamBuilder
    need_patch_recycle_host_details = True
    default_need_itsm = False
    default_need_manual_confirm = False

    def supplement_old_nodes(self):
        self.ticket.details["old_nodes"] = {"instance": []}
        seen = set()
        for info in self.ticket.details["infos"]:
            key = (info["ip"], info["bk_cloud_id"])
            if key in seen:
                continue
            seen.add(key)
            machine_info = Machine.objects.filter(ip=info["ip"], bk_cloud_id=info["bk_cloud_id"]).values(
                "ip", "bk_biz_id", "bk_host_id", "bk_cloud_id"
            )
            if machine_info.exists():
                self.ticket.details["old_nodes"]["instance"].append(machine_info[0])

    def patch_ticket_detail(self):
        self.supplement_old_nodes()
        super().patch_ticket_detail()
