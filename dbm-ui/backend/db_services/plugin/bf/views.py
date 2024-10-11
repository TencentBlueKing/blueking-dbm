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
import logging

from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend import env
from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine
from backend.db_services.plugin.bf.serializers import HasBFPrivSerializer
from backend.db_services.plugin.constants import SWAGGER_TAG

logger = logging.getLogger("root")


class BFPluginViewSet(viewsets.SystemViewSet):
    default_permission_class = []

    @common_swagger_auto_schema(
        operation_summary=_("是否具有BF机器权限"),
        request_body=HasBFPrivSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=HasBFPrivSerializer)
    def has_host_bf_access(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        host = data["host"]
        try:
            machine = Machine.objects.get(bk_host_id=host["bk_host_id"])
        except Machine.DoesNotExist:
            logger.warning(_("主机{}不存在业务{}下").format(host["bk_host_innerip"], host["bk_biz_id"]))
            return Response(False)

        # 如果用户属于业务DBA，则拥有机器的bf权限
        machine_db_type = ClusterType.cluster_type_to_db_type(machine.cluster_type)
        biz_dba_admins = DBAdministrator.get_biz_db_type_admins(bk_biz_id=machine.bk_biz_id, db_type=machine_db_type)
        has_bf_access = data["username"] in biz_dba_admins

        return Response(has_bf_access)

    @common_swagger_auto_schema(
        operation_summary=_("放行BF申请的白名单业务"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def list_bf_biz_whitelist(self, request, *args, **kwargs):
        # 目前默认只认为默认DBM业务才能申请
        bf_biz_whitelist = SystemSettings.get_setting_value(
            SystemSettingsEnum.BF_WHITELIST_BIZS, default=[env.DBA_APP_BK_BIZ_ID]
        )
        return Response(bf_biz_whitelist)
