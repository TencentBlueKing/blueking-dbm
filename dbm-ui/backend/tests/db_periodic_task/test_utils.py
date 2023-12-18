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
import logging
import math
import random
import statistics
from typing import List, Set

import pytest

from backend.db_periodic_task import utils
from backend.utils import basic

pytestmark = pytest.mark.django_db
logger = logging.getLogger("test")


class TestCountDownPolicyCompare:
    def test_compare_policy(self):
        queue_lengths = [int(random.random() * 2 * utils.DURATION * math.pow(10, exp)) for exp in range(-1, 3)]
        countdown_funcs = [
            utils.calculate_countdown__mod,
            utils.calculate_countdown__random,
            utils.calculate_countdown__mix,
        ]
        for countdown_func in countdown_funcs:
            variance_list = []
            for queue_length in queue_lengths:
                hit_per_second: List[int] = [0] * utils.DURATION
                for idx in range(queue_length):
                    countdown = countdown_func(count=queue_length, index=idx, duration=utils.DURATION)
                    hit_per_second[countdown] += 1

                hit_per_interval = []
                for chunk in basic.chunk_lists(lst=hit_per_second, n=max(1, int(utils.DURATION / 15))):
                    hit_per_interval.append(sum(chunk))
                print(f"queue_length -> {queue_length}, hit_per_interval -> {hit_per_interval}")
                variance_list.append(statistics.variance(hit_per_interval))

            print(f"{countdown_func.__name__}, variance_list -> {variance_list}")


class TestPeriodicTask:
    def test_calculate_countdown(self):
        def _get_countdown_set(_count: int) -> Set[int]:
            _countdown_set = set()
            for idx in range(_count):
                _countdown_set.add(utils.calculate_countdown(count=_count, index=idx))
            return _countdown_set

        def _test_one_count():
            assert utils.calculate_countdown(count=1, index=0) == 0

        def _test_count_less_than_duration():
            count = random.randint(1, utils.DURATION)
            _get_countdown_set(_count=count)

        def _test_count_more_than_duration():
            count = random.randint(utils.DURATION + 1, 2 * utils.DURATION)
            _get_countdown_set(_count=count)

        _test_one_count()
        _test_count_less_than_duration()
        _test_count_more_than_duration()
