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

import dateutil
import pytz
from django.utils import timezone
from rest_framework import serializers

from backend.constants import DEFAULT_TIME_ZONE_AREA
from backend.utils.time import datetime2str, timestamp2str


class DBTimezoneField(serializers.CharField):
    """
    DB时间通用字段，涉及到时间敏感单据，时间字段统一用这个DBTimezoneField，将时间转换为带时区的时间
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_representation(self, value):
        """转换为带时区的时间"""
        return datetime2str(value)

    def to_internal_value(self, data):
        """转换为带时区的时间"""
        try:
            # 兼容传递进来的是时间戳格式
            data = timestamp2str(int(data))
        except ValueError:
            o_datetime = dateutil.parser.parse(data)
            if not timezone.is_aware(o_datetime):
                # raise serializers.ValidationError(_("请输入带时区的时间"))
                # TODO: 暂时将时间转换为东八区，前端适配后删除
                data = pytz.timezone(DEFAULT_TIME_ZONE_AREA).localize(o_datetime).isoformat()

        return data
