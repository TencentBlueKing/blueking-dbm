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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import StorageInstance
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.ticket import builders
from backend.ticket.builders.common.constants import OperaObjType
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import TicketType


class MongoDBInstanceReloadDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class InstanceReloadDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
        bk_host_id = serializers.IntegerField(help_text=_("实例主机ID"), required=False)
        instance_id = serializers.IntegerField(help_text=_("实例ID"), required=False)
        port = serializers.IntegerField(help_text=_("实例Port"), required=False)
        role = serializers.CharField(help_text=_("角色"), required=False)

    infos = serializers.ListSerializer(help_text=_("重启信息"), child=InstanceReloadDetailSerializer())
    force = serializers.BooleanField(help_text=_("重启策略开关"), required=False, default=False)
    target_select_mode = serializers.ChoiceField(
        help_text=_("目标选择模式"),
        choices=OperaObjType.get_choices(),
        default=OperaObjType.INSTANCE,
    )

    def validate(self, attrs):
        target_select_mode = attrs["target_select_mode"]
        required_fields_map = {
            OperaObjType.CLUSTER: ["cluster_id"],
            OperaObjType.MACHINE: ["bk_host_id"],
            OperaObjType.INSTANCE: ["cluster_id", "bk_host_id", "instance_id", "port"],
        }
        required_fields = required_fields_map[target_select_mode]

        for index, info in enumerate(attrs["infos"]):
            missing_fields = [field for field in required_fields if field not in info]
            if missing_fields:
                raise serializers.ValidationError(
                    {"infos": _("第{}项缺少必填字段: {}").format(index + 1, ", ".join(missing_fields))}
                )

        return attrs


class MongoDBInstanceReloadFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.instance_restart

    @staticmethod
    def _get_storage_cluster(storage):
        return storage.cluster.first()

    def format_ticket_data(self):
        target_select_mode = self.ticket_data["target_select_mode"]
        if target_select_mode == OperaObjType.CLUSTER:
            self.format_cluster_ticket_data()
        elif target_select_mode == OperaObjType.MACHINE:
            self.format_machine_ticket_data()
        else:
            self.format_instance_ticket_data()

    def format_instance_ticket_data(self):
        storage_filters = reduce(
            operator.or_, [Q(machine=info["bk_host_id"], port=info["port"]) for info in self.ticket_data["infos"]]
        )
        storages_map = {
            f"{storage.machine.bk_host_id}:{storage.port}": storage
            for storage in StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(storage_filters)
        }
        for info in self.ticket_data["infos"]:
            storage = storages_map[f"{info['bk_host_id']}:{info['port']}"]
            cluster = self._get_storage_cluster(storage)
            info.update(
                role=storage.machine_type,
                ip=storage.machine.ip,
                bk_cloud_id=cluster.bk_cloud_id,
                db_version=cluster.major_version,
            )

    def format_cluster_ticket_data(self):
        cluster_ids = [info["cluster_id"] for info in self.ticket_data["infos"]]
        storages = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(cluster__id__in=cluster_ids)
            .order_by("machine__bk_host_id", "port")
        )
        cluster_id__storages = {}
        for storage in storages:
            cluster_id__storages.setdefault(self._get_storage_cluster(storage).id, []).append(storage)

        for info in self.ticket_data["infos"]:
            cluster_storages = cluster_id__storages[info["cluster_id"]]
            storage = cluster_storages[0]
            cluster = self._get_storage_cluster(storage)
            info.update(
                role=storage.machine_type,
                bk_cloud_id=cluster.bk_cloud_id,
                db_version=cluster.major_version,
            )
            info.pop("port", None)

    def format_machine_ticket_data(self):
        bk_host_ids = [info["bk_host_id"] for info in self.ticket_data["infos"]]
        storages = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(machine__bk_host_id__in=bk_host_ids)
            .order_by("machine__bk_host_id", "port")
        )
        bk_host_id__storages = {}
        for storage in storages:
            bk_host_id__storages.setdefault(storage.machine.bk_host_id, []).append(storage)

        for info in self.ticket_data["infos"]:
            host_storages = bk_host_id__storages[info["bk_host_id"]]
            storage = host_storages[0]
            cluster = self._get_storage_cluster(storage)
            info.update(
                ip=storage.machine.ip,
                role=storage.machine_type,
                bk_cloud_id=cluster.bk_cloud_id,
                db_version=cluster.major_version,
            )
            info.pop("cluster_id", None)
            info.pop("port", None)


@builders.BuilderFactory.register(TicketType.MONGODB_INSTANCE_RELOAD)
class MongoDBInstanceReloadApplyFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBInstanceReloadDetailSerializer
    inner_flow_builder = MongoDBInstanceReloadFlowParamBuilder
    inner_flow_name = _("MongoDB 实例重启")
    need_patch_instance_details = True
