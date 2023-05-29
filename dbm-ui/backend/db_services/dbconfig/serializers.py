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

from backend.components.dbconfig.constants import ConfType, LevelName, OpType
from backend.db_meta.enums import ClusterType
from backend.db_services.dbconfig import mock_data


class DBConfigBaseSerializer(serializers.Serializer):
    meta_cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    conf_type = serializers.ChoiceField(help_text=_("配置类型"), choices=ConfType.get_choices(), default=ConfType.DBCONF)


class CommonConfigItemSerializer(serializers.Serializer):
    conf_name = serializers.CharField(help_text=_("参数项"))
    flag_locked = serializers.IntegerField(help_text=_("是否锁定"), min_value=0, max_value=1, default=0)
    op_type = serializers.ChoiceField(help_text=_("操作类型"), choices=OpType.get_choices())


class PublicConfigItemSerializer(CommonConfigItemSerializer):
    description = serializers.CharField(help_text=_("描述"), allow_blank=True)
    need_restart = serializers.IntegerField(help_text=_("是否重启实例生效"), min_value=0, max_value=1, default=0)
    value_allowed = serializers.CharField(help_text=_("参数范围"), allow_blank=True)
    value_default = serializers.CharField(help_text=_("参数值"), allow_blank=True)
    value_type = serializers.CharField(help_text=_("参数值类型"), default="STRING")
    value_type_sub = serializers.CharField(help_text=_("参数范围类型，ENUM/REGEX"), allow_blank=True)


class CreatePublicConfigSerializer(DBConfigBaseSerializer):
    version = serializers.CharField(help_text=_("数据库版本"))
    name = serializers.CharField(help_text=_("配置文件名"))
    conf_items = serializers.ListSerializer(help_text=_("配置项列表"), child=PublicConfigItemSerializer())
    confirm = serializers.IntegerField(help_text=_("是否确认"), min_value=0, max_value=1, default=0)
    description = serializers.CharField(help_text=_("配置文件描述"), allow_blank=True, default="")
    publish_description = serializers.CharField(help_text=_("发布描述"), allow_blank=True, default="")

    class Meta:
        swagger_schema_fields = {"example": mock_data.CREATE_PUBLIC_CONFIG_REQUEST_BODY}


class GetPublicConfigDetailSerializer(DBConfigBaseSerializer):
    version = serializers.CharField(help_text=_("数据库版本"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.GET_PUBLIC_CONFIG_DETAIL_REQUEST_BODY}


class ListPublicConfigRequestSerializer(DBConfigBaseSerializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.LIST_PUBLIC_CONFIG_REQUEST_BODY}


class ListPublicConfigResponseSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("配置文件名"))
    version = serializers.CharField(help_text=_("数据库版本"))
    updated_at = serializers.DateTimeField(help_text=_("更新时间"))
    updated_by = serializers.DateTimeField(help_text=_("更新人"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.LIST_PUBLIC_CONFIG_RESPONSE_DATA}


class ListBizConfigRequestSerializer(DBConfigBaseSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))

    class Meta:
        swagger_schema_fields = {"example": mock_data.LIST_PUBLIC_CONFIG_REQUEST_BODY}


class LevelConfigItemSerializer(CommonConfigItemSerializer):
    conf_value = serializers.CharField(help_text=_("参数值"), allow_blank=True)
    description = serializers.CharField(help_text=_("描述"), required=False, allow_blank=True, default="")


class CommonLevelConfigSerializer(DBConfigBaseSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    version = serializers.CharField(help_text=_("数据库版本"))
    level_name = serializers.ChoiceField(help_text=_("层级名称"), choices=LevelName.get_choices())
    level_value = serializers.CharField(help_text=_("层级值"))
    level_info = serializers.DictField(help_text=_("层级关系"), required=False)


class UpsertLevelConfigSerializer(CommonLevelConfigSerializer):
    conf_items = serializers.ListSerializer(help_text=_("配置项列表"), child=LevelConfigItemSerializer())
    confirm = serializers.IntegerField(help_text=_("是否确认"), min_value=0, max_value=1, default=0)
    description = serializers.CharField(help_text=_("配置文件描述"), required=False, allow_blank=True, default="")
    publish_description = serializers.CharField(help_text=_("发布描述"), required=False, allow_blank=True, default="")

    class Meta:
        swagger_schema_fields = {"example": mock_data.UPSERT_LEVEL_CONFIG_REQUEST_BODY}


class SaveModuleDeployInfoSerializer(UpsertLevelConfigSerializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.SAVE_MODULE_DEPLOY_INFO_REQUEST_BODY}


class GetLevelConfigDetailSerializer(CommonLevelConfigSerializer):
    class Meta:
        swagger_schema_fields = {"example": mock_data.GET_LEVEL_CONFIG_DETAIL_REQUEST_BODY}


class GetConfigVersionDetailSerializer(CommonLevelConfigSerializer):
    revision = serializers.CharField(help_text=_("历史版本号"))
