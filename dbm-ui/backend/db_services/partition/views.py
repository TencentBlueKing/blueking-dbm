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
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components.mysql_partition.client import DBPartitionApi
from backend.db_services.partition.serializers import (
    PartitionColumnVerifyResponseSerializer,
    PartitionColumnVerifySerializer,
    PartitionCreateSerializer,
    PartitionDeleteSerializer,
    PartitionDisableSerializer,
    PartitionDryRunResponseSerializer,
    PartitionDryRunSerializer,
    PartitionEnableSerializer,
    PartitionListResponseSerializer,
    PartitionListSerializer,
    PartitionLogResponseSerializer,
    PartitionLogSerializer,
    PartitionRunSerializer,
    PartitionUpdateSerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

from ...db_meta.models import Cluster
from ...ticket.constants import TicketStatus
from ...ticket.models import Ticket
from ...utils.time import remove_timezone
from .constants import SWAGGER_TAG
from .handlers import PartitionHandler


class DBPartitionViewSet(viewsets.AuditedModelViewSet):

    pagination_class = None

    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @staticmethod
    def _update_log_status(log_list):
        # 更新分区日志的状态
        ticket_ids = [info["ticket_id"] for info in log_list if info["ticket_id"]]
        ticket_id__ticket_map = {ticket.id: ticket for ticket in Ticket.objects.filter(id__in=ticket_ids)}
        for info in log_list:
            ticket = ticket_id__ticket_map.get(info["ticket_id"], None)
            info["status"] = ticket.status if ticket else (info["status"] or TicketStatus.PENDING)

        return log_list

    @common_swagger_auto_schema(
        operation_summary=_("获取分区策略列表"),
        query_serializer=PartitionListSerializer(),
        responses={status.HTTP_200_OK: PartitionListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionListSerializer, representation=True)
        partition_data = DBPartitionApi.query_conf(params=validated_data)

        partition_list = self._update_log_status(partition_data["items"])
        # 去掉时区时间
        for info in partition_list:
            for time_field in ["create_time", "update_time", "execute_time"]:
                info[time_field] = remove_timezone(info[time_field])

        return Response({"count": partition_data["count"], "results": partition_list})

    @common_swagger_auto_schema(
        operation_summary=_("修改分区策略"),
        request_body=PartitionUpdateSerializer(),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionUpdateSerializer)
        validated_data.update(id=kwargs["pk"])
        return Response(DBPartitionApi.update_conf(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("增加分区策略"),
        request_body=PartitionCreateSerializer(),
        responses={status.HTTP_200_OK: PartitionDryRunResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionCreateSerializer)
        return Response(PartitionHandler.create_and_dry_run_partition(validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("批量删除分区策略"),
        request_body=PartitionDeleteSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["DELETE"], detail=False, serializer_class=PartitionDeleteSerializer)
    def batch_delete(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionDeleteSerializer, representation=True)
        return Response(DBPartitionApi.del_conf(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("禁用分区策略"),
        request_body=PartitionDisableSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionDisableSerializer)
    def disable(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionDisableSerializer, representation=True)
        return Response(DBPartitionApi.disable_partition(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("启用分区策略"),
        request_body=PartitionEnableSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionEnableSerializer)
    def enable(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionEnableSerializer, representation=True)
        return Response(DBPartitionApi.enable_partition(params=validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("查询分区策略日志"),
        query_serializer=PartitionLogSerializer(),
        responses={status.HTTP_200_OK: PartitionLogResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=PartitionLogSerializer)
    def query_log(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionLogSerializer, representation=True)
        partition_log_data = DBPartitionApi.query_log(params=validated_data)
        partition_log_list = self._update_log_status(partition_log_data["items"])
        return Response({"count": partition_log_data["count"], "results": partition_log_list})

    @common_swagger_auto_schema(
        operation_summary=_("分区策略前置执行"),
        request_body=PartitionDryRunSerializer(),
        responses={status.HTTP_200_OK: PartitionDryRunResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionDryRunSerializer)
    def dry_run(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionDryRunSerializer, representation=True)
        cluster = Cluster.objects.get(id=validated_data["cluster_id"])
        validated_data.update(
            immute_domain=cluster.immute_domain,
            bk_cloud_id=cluster.bk_cloud_id,
            cluster_type=cluster.cluster_type,
            bk_biz_id=cluster.bk_biz_id,
        )
        dry_run_data = DBPartitionApi.dry_run(params=validated_data, raw=True)
        return Response(PartitionHandler.get_dry_run_data((validated_data, dry_run_data)))

    @common_swagger_auto_schema(
        operation_summary=_("分区策略执行"),
        request_body=PartitionRunSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionRunSerializer)
    def execute_partition(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionRunSerializer, representation=True)
        cluster = Cluster.objects.get(id=validated_data["cluster_id"])
        validated_data.update(
            immute_domain=cluster.immute_domain, bk_cloud_id=cluster.bk_cloud_id, bk_biz_id=cluster.bk_biz_id
        )
        return Response(PartitionHandler.execute_partition(user=request.user.username, **validated_data))

    @common_swagger_auto_schema(
        operation_summary=_("分区策略字段校验"),
        request_body=PartitionColumnVerifySerializer(),
        responses={status.HTTP_500_INTERNAL_SERVER_ERROR: PartitionColumnVerifyResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=PartitionColumnVerifySerializer)
    def verify_partition_field(self, request, *args, **kwargs):
        validated_data = self.params_validate(PartitionColumnVerifySerializer, representation=True)
        cluster = Cluster.objects.get(id=validated_data["cluster_id"])
        validated_data.update(bk_biz_id=cluster.bk_biz_id)
        return Response(PartitionHandler.verify_partition_field(**validated_data))
