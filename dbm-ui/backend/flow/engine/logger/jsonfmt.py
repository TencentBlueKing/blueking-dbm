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
import functools
import json
import logging
import types
from logging import LogRecord

REMOVE_ATTR = [
    "filename",
    "module",
    "exc_text",
    "stack_info",
    "created",
    "msecs",
    "relativeCreated",
    "exc_info",
    "msg",
    "args",
    "thread",
    "threadName",
    "processName",
    "process",
    "name",
    "levelno",
]


class JSONFormatter(logging.Formatter):
    def format(self, record: LogRecord):
        extra = self.build_record(record)
        self.set_format_time(extra)
        if isinstance(record.msg, dict):
            extra["msg"] = json.dumps(record.msg, indent=2, ensure_ascii=False)
        else:
            if record.args:
                extra["msg"] = "'" + record.msg + "'," + str(record.args).strip("()")
            else:
                extra["msg"] = record.msg
        if record.exc_info:
            extra["exc_info"] = self.formatException(record.exc_info)
        if self._fmt == "pretty":
            return json.dumps(extra, indent=1, ensure_ascii=False)
        else:
            return json.dumps(extra, ensure_ascii=False)

    @classmethod
    def build_record(cls, record: LogRecord):
        return {attr_name: record.__dict__[attr_name] for attr_name in record.__dict__ if attr_name not in REMOVE_ATTR}

    @classmethod
    def set_format_time(cls, extra):
        now = datetime.datetime.utcnow()
        format_time = now.strftime("%Y-%m-%dT%H:%M:%S" + ".%03d" % (now.microsecond / 1000) + "Z")
        extra["time"] = format_time
        return format_time
