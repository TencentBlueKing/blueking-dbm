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
import asyncio
import json
import logging
import random
import time
from collections import defaultdict
from typing import Dict, List

from aiokafka import AIOKafkaProducer

from backend import env
from backend.db_proxy.reverse_api.common.impl.sync_report.producer import SingletonKafkaProducer
from backend.db_proxy.reverse_api.common.impl.sync_report.schema_validate import events_validate

logger = logging.getLogger("root")


def sync_report(bk_cloud_id: int, ip: str, port_list: List[int], data: Dict):
    """
    写入 kafka
    """
    events_validate(events=data)

    SingletonKafkaProducer.loop().run_until_complete(
        _write_event(bk_cloud_id, ip, brokers=env.REVERSE_REPORT_KAFKA_BROKER, events=data)
    )


def group_events(bk_cloud_id, ip, events):
    group_by = defaultdict(list)
    for ev in events:
        cluster_type = ev.get("cluster_type", "None")
        event_type = ev.get("event_type", "None")
        topic = f"{cluster_type}-{event_type}"
        group_by[topic].append(
            json.dumps(
                {**ev, "event_source_ip": ip, "event_receive_timestamp": time.time(), "event_bk_cloud_id": bk_cloud_id}
            ).encode("utf-8")
        )

    return group_by


async def _write_event(bk_cloud_id, ip, brokers, events):
    producer = await SingletonKafkaProducer.get_producer(bootstrap_servers=brokers)

    gevents = group_events(bk_cloud_id=bk_cloud_id, ip=ip, events=events)

    tasks = []

    for group_topic, values in gevents.items():
        batch = producer.create_batch()
        for value in values:
            metadata = batch.append(key=None, value=value, timestamp=None)
            if metadata is None:
                partitions = await producer.partitions_for(topic=group_topic)
                partition = random.choice(tuple(partitions))
                tasks.append(
                    SingletonKafkaProducer.loop().create_task(_send_batch(producer, batch, group_topic, partition))
                )
                batch = producer.create_batch()
                continue

        partitions = await producer.partitions_for(topic=group_topic)
        partition = random.choice(tuple(partitions))
        tasks.append(SingletonKafkaProducer.loop().create_task(_send_batch(producer, batch, group_topic, partition)))

    await asyncio.wait(tasks)
    await producer.flush()


async def _send_batch(producer: AIOKafkaProducer, batch, topic, partition):
    await producer.send_batch(batch=batch, topic=topic, partition=partition)
