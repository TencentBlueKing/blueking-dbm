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

from backend.ticket.constants import TicketStatus


class BillStatusTrackerInputSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    bill_id = serializers.IntegerField(help_text=_("单据 ID"))


class BillStatusTrackerOutputSerializer(serializers.Serializer):
    # bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    # bill_id = serializers.IntegerField(help_text=_("单据 ID"))
    status = serializers.ChoiceField(choices=TicketStatus.get_choices(), help_text=_("单据状态"))
    creator = serializers.CharField(help_text=_("建单人"))
    created_at = serializers.TimeField(help_text=_("提单时间"))
    params = serializers.JSONField(help_text=_("单据参数"))
    current_flow = serializers.CharField(help_text=_("当前流程名称"))
    cost_time_seconds = serializers.IntegerField(help_text=_("以秒为单位的耗时"))
    msgs = serializers.ListField(child=serializers.CharField(), help_text=_("单据信息"))
