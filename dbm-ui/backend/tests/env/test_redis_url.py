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
import pytest
from kombu.utils.url import parse_url as kombu_parse_url
from redis.connection import parse_url as redis_parse_url

from backend import env


@pytest.fixture
def redis_conf(monkeypatch):
    def _set(password: str, host: str = "redis.example.com", port: int = 6380):
        monkeypatch.setattr(env, "REDIS_PASSWORD", password)
        monkeypatch.setattr(env, "REDIS_HOST", host)
        monkeypatch.setattr(env, "REDIS_PORT", port)

    return _set


class TestBuildRedisUrl:
    def test_without_password(self, redis_conf):
        redis_conf("")
        assert env.build_redis_url(3) == "redis://redis.example.com:6380/3"

    @pytest.mark.parametrize("password", ["plain", "p@ss:w/rd", "a,b%c#d?e", "$HOME"])
    def test_password_round_trip(self, redis_conf, password):
        """特殊字符经 URL 编码后，redis-py 与 kombu 均能还原原始密码"""
        redis_conf(password)
        url = env.build_redis_url(0)

        redis_kwargs = redis_parse_url(url)
        assert redis_kwargs["password"] == password
        assert redis_kwargs["host"] == "redis.example.com"
        assert redis_kwargs["port"] == 6380
        assert redis_kwargs["db"] == 0

        kombu_kwargs = kombu_parse_url(url)
        assert kombu_kwargs["password"] == password
        assert kombu_kwargs["virtual_host"] == "0"


class TestGetRedisUrlEnv:
    def test_explicit_url_wins(self, redis_conf, monkeypatch):
        redis_conf("pwd")
        monkeypatch.setenv("BROKER_URL", "amqp://guest:guest@rabbitmq:5672/dbm")
        assert env.get_redis_url_env("BROKER_URL", 0) == "amqp://guest:guest@rabbitmq:5672/dbm"

    @pytest.mark.parametrize("explicit", [None, ""])
    def test_unset_or_empty_builds_from_redis(self, redis_conf, monkeypatch, explicit):
        redis_conf("pwd")
        if explicit is None:
            monkeypatch.delenv("CACHE_URL", raising=False)
        else:
            monkeypatch.setenv("CACHE_URL", explicit)
        assert env.get_redis_url_env("CACHE_URL", 5) == "redis://:pwd@redis.example.com:6380/5"
