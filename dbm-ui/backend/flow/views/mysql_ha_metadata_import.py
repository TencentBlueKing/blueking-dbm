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
import uuid

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission
from backend.ticket import constants
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


class UploadMetadataFileSerializer(serializers.Serializer):
    file = serializers.FileField(help_text=_("元数据文件"))
    bk_biz_id = serializers.IntegerField(help_text=_("bk biz id"))
    db_module_id = serializers.IntegerField(help_text=_("db module id"))
    proxy_spec_id = serializers.IntegerField(help_text=_("proxy spec id"))
    storage_spec_id = serializers.IntegerField(help_text=_("storage spec id"))


class TenDBHAMetadataImportViewSet(viewsets.SystemViewSet):
    # permission_classes = [AllowAny]
    serializer_class = UploadMetadataFileSerializer
    http_method_names = ["post"]
    parser_classes = [MultiPartParser]

    def _get_custom_permissions(self):
        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(operation_summary=_("tendbha 元数据迁移"))
    def create(self, request, *args, **kwargs):
        logger.info(_("开始 TenDBHA 元数据导入场景"))

        slz = self.get_serializer_class()(data=request.data)
        slz.is_valid(raise_exception=True)
        file: InMemoryUploadedFile = slz.validated_data["file"]
        bk_biz_id = slz.validated_data.get("bk_biz_id")
        db_module_id = slz.validated_data.get("db_module_id")
        proxy_spec_id = slz.validated_data.get("proxy_spec_id")
        storage_spec_id = slz.validated_data.get("storage_spec_id")

        with file.open("rb") as upload_file:
            content = json.load(upload_file)
            logger.info("content: {}".format(content))
            # 这里需要先做些检查 ToDo
            # 1. db module, proxy spec, storage spec 存在
            # 2. 集群版本和字符集满足 db module 的要求
            # 3. 集群机器配置符合 spec

            root_id = uuid.uuid1().hex
            logger.info("define root_id: {}".format(root_id))

            ticket = Ticket.objects.create(
                bk_biz_id=bk_biz_id,
                ticket_type=constants.TicketType.MYSQL_HA_METADATA_IMPORT,
                group=DBType.MySQL,
                status=constants.TicketStatus.RUNNING,
                remark="",
                details={},
                is_reviewed=True,
                creator=request.user.username,
                updater=request.user.username,
            )

            c = MySQLController(
                root_id=root_id,
                ticket_data={
                    # **request.data,
                    "uid": ticket.id,
                    "json_content": content,
                    "bk_biz_id": bk_biz_id,
                    "proxy_spec_id": proxy_spec_id,
                    "storage_spec_id": storage_spec_id,
                    "db_module_id": db_module_id,
                    "created_by": request.user.username,
                    "ticket_type": constants.TicketType.MYSQL_HA_METADATA_IMPORT,
                },
            )
            c.mysql_ha_metadata_import_scene()

            return Response({"root_id": root_id})
