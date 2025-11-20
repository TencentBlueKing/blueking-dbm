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
import logging
import uuid
from typing import List

from backend import env
from backend.db_proxy.reverse_api.common.impl.sync_report.direct_mode.direct_report import direct_report
from backend.db_proxy.reverse_api.common.impl.sync_report.inject_fields import inject_fields
from backend.db_proxy.reverse_api.common.impl.sync_report.kafka_mode.kafka_report import kafka_report
from backend.db_proxy.reverse_api.common.impl.sync_report.schema_validate import SyncReportEventSerializer
from backend.db_proxy.reverse_api.exceptions import SyncReportBadMode, SyncReportEventValidationException

logger = logging.getLogger("root")

# 避免热点
reverse_report_mode = env.REVERSE_REPORT_MODE.upper()
if reverse_report_mode == "KAFKA":
    report_handler = kafka_report
elif reverse_report_mode == "DIRECT":
    report_handler = direct_report
else:
    raise SyncReportBadMode(mode=reverse_report_mode)


def sync_report(bk_cloud_id: int, ip: str, port_list: List[int], data: List):
    trace_id = uuid.uuid1().__str__()
    logger.info("enter sync report. trace_id:{}, time:{}, data:{}".format(trace_id, datetime.datetime.now(), data))

    vd = SyncReportEventSerializer(data=data, many=True)
    logger.info("sync report slz created. trace_id:{}, time:{}".format(trace_id, datetime.datetime.now()))
    if not vd.is_valid():
        raise SyncReportEventValidationException(
            errors=[{"event": data[idx], "reason": str(err)} for idx, err in enumerate(vd.errors) if err]
        )
    logger.info("sync report validate finish. trace_id:{}, time:{}".format(trace_id, datetime.datetime.now()))

    events = inject_fields(bk_cloud_id=bk_cloud_id, ip=ip, data=data)

    report_handler(bk_cloud_id=bk_cloud_id, trace_id=trace_id, ip=ip, port_list=port_list, events=events)
