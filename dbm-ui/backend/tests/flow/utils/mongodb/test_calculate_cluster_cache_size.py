# -*- coding: utf-8 -*-
"""mongod cacheSizeGB 按机器内存分档分配规则测试"""

import pytest

from backend.flow.consts import MongoDBTotalCache
from backend.flow.utils.mongodb.calculate_cluster import get_cache_percent, get_cache_size


@pytest.mark.parametrize(
    ("memory_mb", "expected_percent"),
    [
        (1 * 1024, MongoDBTotalCache.Cache_Percent_Small.value),  # 1G -> 25%
        (4 * 1024, MongoDBTotalCache.Cache_Percent_Small.value),  # 4G -> 25%
        (5 * 1024, MongoDBTotalCache.Cache_Percent_Medium.value),  # 5G -> 40%
        (16 * 1024, MongoDBTotalCache.Cache_Percent_Medium.value),  # 16G -> 40%
        (17 * 1024, MongoDBTotalCache.Cache_Percent_Large.value),  # 17G -> 50%
        (32 * 1024, MongoDBTotalCache.Cache_Percent_Large.value),  # 32G -> 50%
    ],
)
def test_get_cache_percent_tiers(memory_mb, expected_percent):
    assert get_cache_percent(memory_mb) == expected_percent


@pytest.mark.parametrize(
    ("memory_mb", "num", "expected_gb"),
    [
        (4 * 1024, 1, 1),  # 4G * 25% = 1G
        (16 * 1024, 1, 6),  # 16G * 40% = 6.4 -> int 6
        (32 * 1024, 1, 16),  # 32G * 50% = 16G
        (32 * 1024, 2, 8),  # 同机 2 实例均分
        (1 * 1024, 1, 1),  # 1G * 25% = 0.25 -> 下限 1G
    ],
)
def test_get_cache_size(memory_mb, num, expected_gb):
    assert get_cache_size(memory_size=memory_mb, num=num) == expected_gb
