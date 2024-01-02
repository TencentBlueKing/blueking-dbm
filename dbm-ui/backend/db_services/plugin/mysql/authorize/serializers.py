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


class AuthorizeApplySerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    user = serializers.CharField(help_text=_("授权账号"))
    access_db = serializers.CharField(help_text=_("准入DB"))
    source_ips = serializers.CharField(help_text=_("源IP列表"))
    target_instance = serializers.CharField(help_text=_("目标域名"))
    # gcs专属
    app = serializers.CharField(help_text=_("GCS业务缩写，如qxzb"), required=False)
    set_name = serializers.CharField(help_text=_("Set名称，多个以逗号分隔"), required=False)
    module_host_info = serializers.CharField(help_text=_("模块主机信息"), required=False)
    module_name_list = serializers.CharField(help_text=_("模块列表，多个以逗号分隔"), required=False)
    type = serializers.CharField(help_text=_("类型"), required=False)
    operator = serializers.CharField(help_text=_("操作人"), required=False)

    def validate(self, attrs):
        if not attrs.get("app") and not attrs.get("bk_biz_id"):
            raise serializers.ValidationError(_("请保证至少输入bk_biz_id或者输入app其中之一"))

        return attrs


class AuthorizeApplyResponseSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(help_text=_("任务ID"))
    platform = serializers.CharField(help_text=_("平台"))

    class Meta:
        swagger_schema_fields = {"example": {"task_id": 1, "platform": "gcs/dbm"}}


class QueryAuthorizeApplySerializer(serializers.Serializer):
    task_id = serializers.IntegerField(help_text=_("任务ID"))
    platform = serializers.CharField(help_text=_("平台"))


class QueryAuthorizeApplyResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text=_("状态"))
    msg = serializers.CharField(help_text=_("返回信息"))
