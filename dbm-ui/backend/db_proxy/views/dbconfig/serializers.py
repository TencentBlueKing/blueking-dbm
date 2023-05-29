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

from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_proxy.views import mock_data
from backend.db_proxy.views.serialiers import BaseProxyPassSerialier
from backend.flow.consts import ConfigTypeEnum


class QueryConfItemSerializer(BaseProxyPassSerialier):
    bk_biz_id = serializers.CharField(help_text=_("业务ID"))
    conf_file = serializers.CharField(help_text=_("conf_file 可以是,号分隔的多个文件名，返回结果是一个按照配置文件名组合的一个 list"))
    conf_name = serializers.CharField(
        help_text=_("指定要查询的 conf_name， 多个值以,分隔，为空表示查询该 conf_file 的所有conf_name"),
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    conf_type = serializers.ChoiceField(help_text=_("配置类型"), choices=ConfigTypeEnum.get_choices())
    format = serializers.ChoiceField(help_text=_("format格式"), choices=FormatType.get_choices())
    level_info = serializers.DictField(help_text=_("上层级信息"), required=False)
    level_name = serializers.ChoiceField(help_text=_("配置层级名"), choices=LevelName.get_choices())
    level_value = serializers.CharField(help_text=_("配置层级值"))
    namespace = serializers.CharField(help_text=_("命名空间，一般指DB类型"))


class QueryConfItemResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.QUERY_CONF_ITEM_DATA_RESPONSE}


class BatchGetConfItemSerializer(BaseProxyPassSerialier):
    conf_file = serializers.CharField(
        help_text=_("配置文件名，一般配置类型与配置文件一一对应，但如 mysql 5.6, 5.7 两个版本同" "属 dbconf 配置，所以有 MySQL-5.5, MySQL-5.6 两个配置文件")
    )
    conf_name = serializers.CharField(help_text=_("指定要查询的 conf_name，目前仅支持一个"), required=False)
    conf_type = serializers.ChoiceField(help_text=_("配置类型，如 dbconf,backup"), choices=ConfigTypeEnum.get_choices())
    level_name = serializers.ChoiceField(help_text=_("level name"), choices=LevelName.get_choices())
    level_values = serializers.ListField(
        help_text=_("level value列表"), child=serializers.CharField(), required=False, min_length=0
    )
    namespace = serializers.CharField(help_text=_("命名空间，一般指DB类型"))


class BatchGetConfItemResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.BATCH_GET_DATA_RESPONSE}
