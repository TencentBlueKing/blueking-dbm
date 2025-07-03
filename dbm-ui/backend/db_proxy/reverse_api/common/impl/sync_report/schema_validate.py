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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

import backend.db_proxy.reverse_api.common.impl.sync_report as sr
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType


class SyncReportEventSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(min_value=1)
    cluster_type = serializers.ChoiceField(choices=ClusterType.get_choices())
    event_type = serializers.CharField()

    def validate(self, attrs):
        event_type = attrs.get("event_type", "")
        if event_type not in sr.event_type_cache:
            if event_type in SystemSettings.get_setting_value(SystemSettingsEnum.REVERSE_REPORT_EVENT_TYPES):
                with sr.lock:
                    sr.event_type_cache.append(event_type)
            else:
                raise serializers.ValidationError(_(f"{event_type} not a registered event type"))

        return attrs
