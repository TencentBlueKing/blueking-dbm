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
from typing import List

from kafka import KafkaProducer

import backend.db_proxy.reverse_api.common.impl.sync_report as sr
from backend import env
from backend.db_proxy.reverse_api.common.impl.sync_report.kafka_mode.send_event_to_kafka import send_events_to_kafka

logger = logging.getLogger("root")


def kafka_report(bk_cloud_id: int, trace_id: str, ip: str, port_list: List[int], events: List):
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

    logger.info("sync kafka report release lock. trace_id:{}, time:{}".format(trace_id, datetime.datetime.now()))

    producer = random.choice(tuple(sr.producers))
    logger.info("sync kafka report got producer. trace_id:{}, time:{}".format(trace_id, datetime.datetime.now()))

    send_events_to_kafka(producer=producer, bk_cloud_id=bk_cloud_id, ip=ip, events=events)
