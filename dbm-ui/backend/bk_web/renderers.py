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
import datetime
import types
from typing import Any

from django.utils.duration import duration_iso_string
from django.utils.timezone import is_aware
from rest_framework.renderers import JSONRenderer
from rest_framework.utils.encoders import JSONEncoder

from backend.utils.local import local
from backend.utils.time import date2str, datetime2str


class BKJSONEncoder(JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time, decimal types and UUIDs.
    """

    def default(self, o: Any):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.datetime):
            return datetime2str(o)
        elif isinstance(o, datetime.date):
            return date2str(o)
        elif isinstance(o, datetime.time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, datetime.timedelta):
            return duration_iso_string(o)
        elif isinstance(o, set):
            return list(o)
        elif isinstance(o, types.FunctionType):
            return str(o)
        else:
            return super().default(o)


class BKAPIRenderer(JSONRenderer):
    """
    采用统一的结构封装返回内容
    """

    encoder_class = BKJSONEncoder
    SUCCESS_CODE = 0
    SUCCESS_MESSAGE = "OK"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, dict) and "code" in data:
            data["request_id"] = local.request_id
        else:
            data = {
                "data": data,
                "code": self.SUCCESS_CODE,
                "message": self.SUCCESS_MESSAGE,
                "request_id": local.request_id,
            }

        if renderer_context:
            for key in ["message", "web_annotations"]:
                if renderer_context.get(key):
                    data[key] = renderer_context[key]

        response = super().render(data, accepted_media_type, renderer_context)
        return response
