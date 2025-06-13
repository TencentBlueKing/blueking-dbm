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
import hashlib
import json
import logging
from typing import Any, Dict

from aiokafka import AIOKafkaProducer

logger = logging.getLogger("root")


class SingletonKafkaProducer:
    _producers: Dict[str, AIOKafkaProducer] = {}
    _lock = asyncio.Lock()
    _loop = asyncio.new_event_loop()

    @classmethod
    def loop(cls):
        return cls._loop

    @classmethod
    async def get_producer(cls, bootstrap_servers: Any) -> AIOKafkaProducer:
        bs_md5 = cls._broker_md5(bootstrap_servers=bootstrap_servers)
        async with cls._lock:
            if bs_md5 not in cls._producers:
                producer = await cls._create_producer(bootstrap_servers=bootstrap_servers)
                cls._producers[bs_md5] = producer

        return cls._producers[bs_md5]

    @classmethod
    async def _create_producer(cls, bootstrap_servers: Any) -> AIOKafkaProducer:
        producer = AIOKafkaProducer(loop=cls._loop, bootstrap_servers=bootstrap_servers)
        await producer.start()
        return producer

    @classmethod
    def _broker_md5(cls, bootstrap_servers: Any) -> str:
        return hashlib.md5(json.dumps(bootstrap_servers).encode("utf-8")).hexdigest()
