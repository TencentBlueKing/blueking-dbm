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
import random
import uuid
from typing import List

from kafka import KafkaProducer

import backend.db_proxy.reverse_api.common.impl.sync_report as sr
from backend import env
from backend.db_proxy.reverse_api.common.impl.sync_report.schema_validate import SyncReportEventSerializer
from backend.db_proxy.reverse_api.common.impl.sync_report.send_event import send_events
from backend.db_proxy.reverse_api.exceptions import SyncReportEventValidationException

logger = logging.getLogger("root")


def sync_report(bk_cloud_id: int, ip: str, port_list: List[int], data: List):
    trace_id = uuid.uuid1()
    logger.info("enter sync report. trace_id:{}, time:{}, data:{}".format(trace_id, datetime.datetime.now(), data))
    kafka_opts = env.REVERSE_REPORT_KAFKA_OPTIONS
    with sr.lock:
        if sr.producers is None:
            logger.info("sync report new kafka connect. time:{}".format(datetime.datetime.now()))
            sr.producers = [
                KafkaProducer(
                    api_version=(0, 11),
                    retries=5,
                    request_timeout_ms=2000,
                    reconnect_backoff_max_ms=2000,
                    max_block_ms=2000,
                    **kafka_opts
                )
                for i in range(5)
            ]

    logger.info("sync report release lock. trace_id:{}, time:{}".format(trace_id, datetime.datetime.now()))

    vd = SyncReportEventSerializer(data=data, many=True)
    logger.info("sync report slz created. trace_id:{}, time:{}".format(trace_id, datetime.datetime.now()))
    if not vd.is_valid():
        raise SyncReportEventValidationException(
            errors=[{"event": data[idx], "reason": str(err)} for idx, err in enumerate(vd.errors) if err]
        )
    logger.info("sync report validate finish. trace_id:{}, time:{}".format(trace_id, datetime.datetime.now()))

    producer = random.choice(tuple(sr.producers))
    logger.info("sync report got producer. trace_id:{}, time:{}".format(trace_id, datetime.datetime.now()))

    send_events(producer=producer, bk_cloud_id=bk_cloud_id, ip=ip, data=data)
