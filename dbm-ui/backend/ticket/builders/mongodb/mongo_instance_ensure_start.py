# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MongoDB 进程拉起单据：仅自愈 Autofix PRE（process_bad）自动跟单，不挂工具箱入口。
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import StorageInstance
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBInstanceEnsureStartDetailSerializer(BaseMongoDBOperateDetailSerializer):
    """单据参数：已监听则跳过 stop/start（无强制重启）。"""

    class InstanceEnsureStartInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_host_id = serializers.IntegerField(help_text=_("实例主机ID"))
        ip = serializers.CharField(help_text=_("IP地址"))
        instance_id = serializers.IntegerField(help_text=_("实例ID"), required=False)
        port = serializers.IntegerField(help_text=_("实例Port"))
        role = serializers.CharField(help_text=_("角色"), required=False)
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=False)
        db_version = serializers.CharField(help_text=_("版本"), required=False)

    infos = serializers.ListSerializer(
        help_text=_("进程拉起信息"), child=InstanceEnsureStartInfoSerializer(), allow_empty=False
    )


class MongoDBInstanceEnsureStartFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.instance_ensure_start

    def format_ticket_data(self):
        for info in self.ticket_data["infos"]:
            if info.get("bk_cloud_id") is not None and info.get("role"):
                continue
            storage = (
                StorageInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id=info["bk_host_id"], port=info["port"])
                .first()
            )
            if not storage:
                continue
            cluster = storage.cluster.first()
            info.setdefault("role", storage.machine_type)
            info.setdefault("ip", storage.machine.ip)
            if cluster:
                info.setdefault("bk_cloud_id", cluster.bk_cloud_id)
                info.setdefault("db_version", cluster.major_version)
                info.setdefault("cluster_id", cluster.id)


@builders.BuilderFactory.register(
    TicketType.MONGODB_INSTANCE_ENSURE_START, is_apply=False, iam=ActionEnum.MONGODB_MANAGE
)
class MongoDBInstanceEnsureStartFlowBuilder(BaseMongoDBTicketFlowBuilder):
    """
    MongoDB 进程拉起。

    前置单据：MONGODB_AUTOFIX_PRE（Autofix）triage → process_bad。
    不设置工具箱入口（勿注册 frontend toolbox / routes）。
    """

    serializer = MongoDBInstanceEnsureStartDetailSerializer
    inner_flow_builder = MongoDBInstanceEnsureStartFlowParamBuilder
    inner_flow_name = _("MongoDB 进程拉起")

    default_need_itsm = True
    default_need_manual_confirm = True

    @property
    def need_itsm(self):
        if "need_itsm" in self.ticket.details:
            return bool(self.ticket.details["need_itsm"])
        return super().need_itsm

    @property
    def need_manual_confirm(self):
        if "need_manual_confirm" in self.ticket.details:
            return bool(self.ticket.details["need_manual_confirm"])
        return super().need_manual_confirm
