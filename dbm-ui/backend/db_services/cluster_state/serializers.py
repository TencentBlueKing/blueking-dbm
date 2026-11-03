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

from backend.db_meta.enums import ClusterType


class StateSchemaQuerySerializer(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())


class StateSchemaResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {
            "example": {
                "cluster_type": "tendbsingle",
                "fields": [
                    {
                        "key": "phase",
                        "name": _("集群阶段"),
                        "help_text": _("集群的启用/禁用阶段，取自 Cluster.phase"),
                        "value_type": "enum",
                        "choices": [
                            {"value": "online", "label": _("正常")},
                            {"value": "offline", "label": _("禁用")},
                        ],
                        "default_value": None,
                        "filterable": True,
                        "writable": False,
                        "drilldown_type": None,
                        "source": "native",
                    },
                    {
                        "key": "running_ticket",
                        "name": _("关联单据"),
                        "help_text": _("集群当前运行中的单据ID列表，取自集群操作记录 ClusterOperateRecord"),
                        "value_type": "multi",
                        "choices": [],
                        "default_value": [],
                        "filterable": True,
                        "writable": False,
                        "drilldown_type": "TICKET_LIST",
                        "source": "native",
                    },
                ],
                "display_fields": ["phase", "status", "running_ticket"],
            }
        }


class StateDetailQuerySerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    key = serializers.CharField(help_text=_("状态字段key"))


class StateDetailResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {
            "example": {
                "type": "table",
                "columns": [
                    {"key": "ticket_id", "name": _("单据ID")},
                    {"key": "ticket_type_display", "name": _("单据类型")},
                ],
                "data": [
                    {"ticket_id": 101, "ticket_type": "MYSQL_SINGLE_APPLY", "ticket_type_display": _("MySQL单节点部署")}
                ],
            }
        }
