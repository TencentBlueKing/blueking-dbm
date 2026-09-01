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

import requests
from bk_monitor_report import MonitorReporter

# 单次上报请求的超时时间(秒)。上游 MonitorReporter 调用 sender.post 时未传 timeout，
# 监控自定义上报地址不可达时，上报线程会一直阻塞到 TCP 默认超时(分钟级)，期间该进程停止上报
REPORT_TIMEOUT_SECONDS = 30


class TimeoutSession(requests.Session):
    """为所有请求补上默认超时的 Session；显式传入 timeout 时以调用方为准。"""

    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", REPORT_TIMEOUT_SECONDS)
        return super().request(*args, **kwargs)


class TimeoutMonitorReporter(MonitorReporter):
    """带超时约束的自定义指标上报器。"""

    def report(self):
        session = TimeoutSession()
        adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        for index, data in enumerate(self.generate_chunked_report_data(), 1):
            self._report(data=data, session=session, chunk=index)

    def _report(self, data: dict, session=None, **extras):
        # report_event 等入口不传 session，上游会回落到无超时的模块级 requests
        super()._report(data=data, session=session or TimeoutSession(), **extras)
