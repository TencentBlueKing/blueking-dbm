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
from datetime import timedelta

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.ticket.constants import TicketStatus, TicketType


class TicketListInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    # ticket_types = serializers.ListField(child=serializers.ChoiceField(choices=TicketType.get_choices()),
    #                                    help_text=_("单据类型"), default=[])
    ticket_ids = serializers.ListField(child=serializers.IntegerField(), help_text=_("单据 ID"), default=[])
    cluster_domains = serializers.ListField(child=serializers.CharField(), help_text=_("集群域名"), default=[])
    statuses = serializers.ListField(
        child=serializers.ChoiceField(choices=TicketStatus.get_choices()), help_text=_("单据状态"), default=[]
    )
    time_duration = serializers.DurationField(help_text=_("单据查询时间范围"), default=timedelta(days=2))


class TicketInfoSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(help_text=_("单据 ID"))
    ticket_url = serializers.URLField(help_text=_("单据链接"))
    ticket_type = serializers.ChoiceField(choices=TicketType.get_labels(), help_text=_("单据类型"))
    creator = serializers.CharField(help_text=_("提单人"))
    helpers = serializers.ListField(child=serializers.CharField(), help_text=_("前 2 个协助人"))
    status = serializers.CharField(help_text=_("单据状态"))
    relate_clusters = serializers.ListField(child=serializers.CharField(), help_text=_("关联集群"))
    created_at = serializers.TimeField(help_text=_("单据创建时间"))
    ticket_param = serializers.JSONField(help_text=_("单据参数"))
    current_flow = serializers.CharField(help_text=_("当前流程"))
    cost_time_seconds = serializers.IntegerField(help_text=_("单据耗时（秒）"))
    msgs = serializers.ListField(child=serializers.CharField(), help_text=_("单据消息"))


class TicketListOutputSerializer(serializers.Serializer):
    ticket_infos = serializers.ListField(child=TicketInfoSerializer(), help_text=_("单据信息"))
    username = serializers.CharField(help_text=_("用户名"))
