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
import json
import logging

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.meta_import.constants import SWAGGER_TAG
from backend.db_services.meta_import.serializers import (
    TenDBClusterAppendCTLSerializer,
    TenDBClusterMetadataImportSerializer,
    TenDBClusterStandardizeSerializer,
    TenDBHAMetadataImportSerializer,
    TenDBHAStandardizeSerializer,
)
from backend.iam_app.handlers.drf_perm import RejectPermission
from backend.ticket.builders.mysql.mysql_ha_metadata_import import TenDBHAMetadataImportDetailSerializer
from backend.ticket.builders.mysql.mysql_ha_standardize import TenDBHAStandardizeDetailSerializer
from backend.ticket.builders.spider.metadata_import import TenDBClusterMetadataImportDetailSerializer
from backend.ticket.builders.spider.mysql_spider_standardize import TenDBClusterStandardizeDetailSerializer
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


class DBMetadataImportViewSet(viewsets.SystemViewSet):

    pagination_class = None

    def _get_custom_permissions(self):
        migrate_users = SystemSettings.get_setting_value(key=SystemSettingsEnum.DBM_MIGRATE_USER, default=[])
        if not self.request.user.is_superuser and self.request.user.username not in migrate_users:
            return [RejectPermission()]
        return []

    @common_swagger_auto_schema(
        operation_summary=_("TenDB HA 元数据导入"),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TenDBHAMetadataImportSerializer,
        parser_classes=[MultiPartParser],
    )
    def tendbha_metadata_import(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        # 解析json文件
        data["json_content"] = json.loads(data.pop("file").read().decode("utf-8"))
        # 自动创建ticket
        TenDBHAMetadataImportDetailSerializer(data=data).is_valid(raise_exception=True)
        Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_HA_METADATA_IMPORT,
            creator=request.user.username,
            bk_biz_id=data["bk_biz_id"],
            remark=self.tendbha_metadata_import.__name__,
            details=data,
        )
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("TenDB HA 标准化接入"),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TenDBHAStandardizeSerializer,
        parser_classes=[MultiPartParser],
    )
    def tendbha_standardize(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())

        domain_list = []
        for line in data.pop("file").readlines():
            domain_list.append(line.decode("utf-8").strip().rstrip("."))

        cluster_ids = list(
            Cluster.objects.filter(immute_domain__in=domain_list, cluster_type=ClusterType.TenDBHA.value).values_list(
                "id", flat=True
            )
        )
        logger.info("domains: {}, ids: {}".format(domain_list, cluster_ids))

        exists_domains = list(
            Cluster.objects.filter(immute_domain__in=domain_list, cluster_type=ClusterType.TenDBHA.value).values_list(
                "immute_domain", flat=True
            )
        )
        diff = list(set(domain_list) - set(exists_domains))
        if diff:
            raise serializers.ValidationError(_("cluster {} not found".format(diff)))

        data["cluster_ids"] = cluster_ids

        data["infos"] = {"cluster_ids": data["cluster_ids"]}
        # 创建标准化ticket
        TenDBHAStandardizeDetailSerializer(data=data).is_valid(raise_exception=True)
        Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_HA_STANDARDIZE,
            creator=request.user.username,
            bk_biz_id=data["bk_biz_id"],
            remark=self.tendbha_standardize.__name__,
            details=data,
        )
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("TenDB Cluster 元数据导入"),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TenDBClusterMetadataImportSerializer,
        parser_classes=[MultiPartParser],
    )
    def tendbcluster_metadata_import(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        data["json_content"] = json.loads(data.pop("file").read().decode("utf-8"))
        TenDBClusterMetadataImportDetailSerializer(data=data).is_valid(raise_exception=True)
        Ticket.create_ticket(
            ticket_type=TicketType.TENDBCLUSTER_METADATA_IMPORT,
            creator=request.user.username,
            bk_biz_id=data["bk_biz_id"],
            remark=self.tendbcluster_metadata_import.__name__,
            details=data,
        )
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("TenDB Cluster 集群标准化"),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TenDBClusterStandardizeSerializer,
        parser_classes=[MultiPartParser],
    )
    def tendbcluster_standardize(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())

        domain_list = []
        for line in data.pop("file").readlines():
            domain_list.append(line.decode("utf-8").strip().rstrip("."))

        cluster_ids = list(
            Cluster.objects.filter(
                immute_domain__in=domain_list, cluster_type=ClusterType.TenDBCluster.value
            ).values_list("id", flat=True)
        )
        logger.info("domains: {}, ids: {}".format(domain_list, cluster_ids))

        exists_domains = list(
            Cluster.objects.filter(
                immute_domain__in=domain_list, cluster_type=ClusterType.TenDBCluster.value
            ).values_list("immute_domain", flat=True)
        )
        diff = list(set(domain_list) - set(exists_domains))
        if diff:
            raise serializers.ValidationError(_("cluster {} not found".format(diff)))

        data["cluster_ids"] = cluster_ids

        data["infos"] = {"cluster_ids": data["cluster_ids"]}
        # 创建标准化ticket
        TenDBClusterStandardizeDetailSerializer(data=data).is_valid(raise_exception=True)
        Ticket.create_ticket(
            ticket_type=TicketType.TENDBCLUSTER_STANDARDIZE,
            creator=request.user.username,
            bk_biz_id=data["bk_biz_id"],
            remark=self.tendbcluster_standardize.__name__,
            details=data,
        )
        return Response(data)

    @common_swagger_auto_schema(
        operation_summary=_("TenDB Cluster 追加部署中控"),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=TenDBClusterAppendCTLSerializer,
        parser_classes=[MultiPartParser],
    )
    def tendbcluster_append_deploy_ctl(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        # 创建标准化ticket
        Ticket.create_ticket(
            ticket_type=TicketType.TENDBCLUSTER_APPEND_DEPLOY_CTL,
            creator=request.user.username,
            bk_biz_id=data["bk_biz_id"],
            remark=self.tendbcluster_append_deploy_ctl.__name__,
            details=data,
        )
        return Response(data)
