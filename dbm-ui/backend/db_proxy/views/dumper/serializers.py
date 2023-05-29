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


class DumperMigrateProxyPassSerializer(BaseProxyPassSerializer):
    class DumperSwitchInfoSerializer(serializers.Serializer):
        class SwitchInstanceSerializer(serializers.Serializer):
            ip = serializers.CharField(help_text=_("主机IP"))
            port = serializers.IntegerField(help_text=_("主机端口"))
            binlog_file = serializers.CharField(help_text=_("待切换后需要同步的binlog文件"))
            binlog_position = serializers.IntegerField(help_text=_("待切换后需要同步的binlog文件的为位点"))

        cluster_domain = serializers.CharField(help_text=_("集群域名"))
        switch_instances = serializers.ListSerializer(help_text=_("dumper切换信息"), child=SwitchInstanceSerializer())

    infos = serializers.ListSerializer(child=DumperSwitchInfoSerializer())
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    is_safe = serializers.BooleanField(help_text=_("是否安全切换"), required=False, default=True)
