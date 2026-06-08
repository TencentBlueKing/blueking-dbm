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

from backend.configuration.models import DBAdministrator
from backend.db_report import mock_data
from backend.db_report.enums import ReportKind


class ReportCommonFieldSerializerMixin(serializers.Serializer):
    """巡检报告通用字段serializer类"""

    dba = serializers.SerializerMethodField(help_text=_("第一BDA"))

    def get_dba_map(self, db_type):
        if hasattr(self, "_dba_map"):
            return self._dba_map
        biz_dba_map = {}
        for dba in DBAdministrator.objects.filter(db_type=db_type).values("bk_biz_id", "users"):
            biz_dba_map[dba["bk_biz_id"]] = dba["users"]

        # 获取平台级别（bk_biz_id=0）的 DBA 配置作为默认值
        platform_dba = DBAdministrator.objects.filter(db_type=db_type, bk_biz_id=0).first()
        platform_users = platform_dba.users if platform_dba and platform_dba.users else []
        # 构建最终的 dba_map，如果业务的 users 为空，则使用平台级别的 users
        self._dba_map = {}
        for bk_biz_id, users in biz_dba_map.items():
            if users and len(users) > 0:
                self._dba_map[bk_biz_id] = users[0]
            elif platform_users and len(platform_users) > 0:
                # 业务的 users 为空，使用平台级别的第一个用户
                self._dba_map[bk_biz_id] = platform_users[0]
            else:
                self._dba_map[bk_biz_id] = ""
        return self._dba_map

    def get_dba(self, obj):
        return self.get_dba_map(self.context["view"].db_type).get(obj.bk_biz_id, "")


class GetReportOverviewSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(help_text=_("类型"), choices=ReportKind.get_choices(), default=ReportKind.INSPECT)

    class Meta:
        swagger_schema_fields = {"example": mock_data.REPORT_OVERVIEW_DATA}


class GetReportCountSerializer(serializers.Serializer):
    time_range = serializers.CharField(help_text=_("时间范围"), required=False, default="")

    class Meta:
        swagger_schema_fields = {"example": mock_data.REPORT_COUNT_DATA}
