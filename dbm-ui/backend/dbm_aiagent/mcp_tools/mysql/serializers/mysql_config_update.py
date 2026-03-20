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

from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_config_update_allowed


class UpdateMysqlConfigInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 id, bk_biz_id"))
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    conf_type = serializers.ChoiceField(
        choices=mysql_config_update_allowed, help_text=_("配置类型: backup, mysql_monitor, checksum")
    )
    conf_file = serializers.CharField(help_text=_("配置文件名"))
    conf_name = serializers.CharField(help_text=_("配置项名称"))
    conf_value = serializers.CharField(help_text=_("配置项值"))


class UpdateMysqlConfigOutputSerializer(serializers.Serializer):
    message = serializers.CharField(help_text=_("修改结果信息"))
