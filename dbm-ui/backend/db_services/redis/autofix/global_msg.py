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
import json

from django.utils import timezone

from backend.utils.redis import RedisConn
from backend.utils.time import datetime2timestamp

from .const import SWITCH_MAX_WAIT_SECONDS


# 全局的
def GetOrSaveSwitchWait(ip, srst):
    k = "redis|autofix|wait|{}".format(ip)
    if not RedisConn.exists(k):
        RedisConn.hset(k, "ip", ip)
        RedisConn.hset(k, "start", datetime2timestamp(datetime.datetime.now(timezone.utc)))
        RedisConn.hset(k, "err", str(srst))  # log: redis.exceptions.DataError: Invalid input of type: 'dict'.
        RedisConn.hset(k, "counter", 1)
        RedisConn.expire(k, SWITCH_MAX_WAIT_SECONDS * 30)  # 30 分钟
    else:
        RedisConn.hincrby(k, "counter", 1)
    vals = RedisConn.hgetall(k)
    return vals


# 切换完成，就可以发起自愈了
def NeedStartAutofix(switched_finished):
    k = "redis|autofix|start|lock|{}|{}".format(switched_finished.ip, switched_finished.cluster_id)
    if RedisConn.setnx(
        k,
        "{}|{}".format(
            datetime2timestamp(datetime.datetime.now(timezone.utc)), json.dumps(switched_finished.__dict__)
        ),
    ):
        RedisConn.expire(k, SWITCH_MAX_WAIT_SECONDS * 50)  # 50 分钟
        RedisConn.hset(
            "redis|autofix|{}".format(switched_finished.cluster_type),
            datetime2timestamp(datetime.datetime.now(timezone.utc)),
            "{}|{}".format(switched_finished.ip, json.dumps(switched_finished.__dict__)),
        )
        return True
    else:
        return False


# cluster 模式 集群｜机器 发起自愈需要有锁
def CanClusterStartAutoFix(immute_domain, ip):
    k = "redis|autofix|cluster|lock|{}|{}".format(immute_domain, ip)
    if RedisConn.setnx(
        k, "{}|{}|{}".format(immute_domain, ip, datetime2timestamp(datetime.datetime.now(timezone.utc)))
    ):
        RedisConn.expire(k, SWITCH_MAX_WAIT_SECONDS * 15)  # 15 分钟
        return True
    else:
        return False
