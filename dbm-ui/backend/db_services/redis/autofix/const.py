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


from dataclasses import dataclass

# 等待切换成功的机器列表
REDIS_SWITCH_WAITER = {}
# 等待的最长时间
SWITCH_MAX_WAIT_SECONDS = 60 * 6
# 来个默认值吧
SWITCH_SMALL = 999999


@dataclass()
class RedisSwitchHost:
    bk_biz_id: int
    cluster_id: int
    cluster_type: str
    immute_domain: str
    instance_type: str
    cluster_ports: list
    bk_host_id: int
    ip: str
    switch_ports: list
    sw_min_id: int
    sw_max_id: int
    sw_result: dict


@dataclass()
class RedisSwitchCluster:
    bk_biz_id: int
    cluster_id: int
    cluster_type: str


@dataclass()
class RedisSwitchWait:
    ip: str
    entry: int
    err: str
    counter: int
