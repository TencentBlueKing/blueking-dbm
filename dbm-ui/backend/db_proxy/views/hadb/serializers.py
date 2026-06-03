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

from backend.db_proxy.views.serialiers import BaseProxyPassSerializer
from backend.exceptions import AppBaseException


class HADBProxyPassSerializer(BaseProxyPassSerializer):
    name = serializers.CharField(help_text=_("名字"), required=False)
    query_args = serializers.JSONField(help_text=_("查询参数"), required=False)
    set_args = serializers.JSONField(help_text=_("设置参数"), required=False)


class QueryOrSetArgsSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False)
    bk_cloud_id = serializers.IntegerField(help_text=_("云ID"), required=False)
    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    cluster_name = serializers.CharField(help_text=_("集群名称"), required=False)
    switch_version = serializers.CharField(help_text=_("版本"), required=False)
    status = serializers.CharField(help_text=_("状态"), required=False)


class HADBBlackWhiteListSerializer(BaseProxyPassSerializer):
    name = serializers.CharField(help_text=_("名字"))
    query_args = QueryOrSetArgsSerializer(required=False, allow_null=True, help_text=_("查询参数"))
    set_args = QueryOrSetArgsSerializer(required=False, allow_null=True, help_text=_("修改参数"))

    def validate(self, attrs):
        if attrs.get("name") == "insert_black_white_list":
            if not (
                attrs["set_args"].get("bk_biz_id")
                and attrs["set_args"].get("cluster_name")
                and attrs["set_args"].get("cluster_id")
                and attrs["set_args"].get("switch_version")
            ):
                raise AppBaseException(_("新增黑白名单必须指定 bk_biz_id 、 cluster_id 、 cluster_name 、 switch_version"))
        elif attrs.get("name") in ["delete_black_white_list", "update_black_white_list"]:
            if not (
                attrs["query_args"].get("id")
                or attrs["query_args"].get("bk_biz_id")
                or attrs["query_args"].get("cluster_name")
                or attrs["query_args"].get("cluster_id")
            ):
                raise AppBaseException(_("必须至少指定 id 、 bk_biz_id 、 cluster_id 、 cluster_name 之一"))

        return attrs
