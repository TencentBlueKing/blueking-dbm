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
import ipaddress
import json

from django.core.serializers.json import DjangoJSONEncoder
from django_redis import get_redis_connection
from django_redis.pool import ConnectionFactory as Factory
from django_redis.serializers.base import BaseSerializer


class JSONSerializer(BaseSerializer):
    """
    自定义JSON序列化器用于redis序列化
    django-redis的默认JSON序列化器假定`decode_responses`被禁用。
    """

    def dumps(self, value):
        return json.dumps(value, cls=DjangoJSONEncoder)

    def loads(self, value):
        return json.loads(value)


class ConnectionFactory(Factory):
    """
    自定义ConnectionFactory以注入decode_responses参数
    """

    def make_connection_params(self, url):
        kwargs = super().make_connection_params(url)
        kwargs["decode_responses"] = True
        return kwargs


# 定义redis的原生客户端
RedisConn = get_redis_connection("default")


def is_valid_ip(ip_address):
    """是否是合法的ip"""
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ipaddress.AddressValueError:
        return False
    except Exception:
        return False
