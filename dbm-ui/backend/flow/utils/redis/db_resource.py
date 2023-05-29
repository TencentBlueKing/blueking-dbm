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
import copy
import logging.config
from typing import Dict, List, Optional

import requests
from django.utils.translation import ugettext as _

from backend.flow.consts import DBConstNumEnum, MediumEnum, RDMSApplyEnum
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")
single_ticket_type = [TicketType.REDIS_SINGLE_APPLY.name]
cluster_ticket_type = [TicketType.REDIS_CLUSTER_APPLY.name]


class RedisResource(object):
    """
    构建Redis资源申请类
    """

    def __init__(self):
        self.proxy_spec = {"cpu": [1, 2], "ram": [2000, 4000], "hdd": [50, 100], "ssd": [0]}
        self.common_param = {
            "count": 0,
            "location_spec": {
                "city": "{city}",
                "cross_switch": True
                # "anti-affinity": "SAME_ZONE"  # 表示申请的机器必须是同园区。默认是跨园区，本地测试来用的
            },
            "spec": {},
            "allowBareMetaToDocker": True,
            "device_class": "{spec}",
            "item": "default",
        }

    def get_payload_params(
        self, city: str, cross_switch: bool, spec: str, group_count: int, ticket_type: str
    ) -> Optional[List]:
        """
        根据单据类型，拼接对应的请求资源参数体
        @city：城市
        @cross_switch: 是否跨园区
        @spec: 规格
        @count: 所需机器组数
        @ticket_type：单据类型
        """
        rms_detail = []
        self.common_param["location_spec"]["city"] = city
        self.common_param["location_spec"]["cross_switch"] = cross_switch
        self.common_param["device_class"] = spec

        # 无论是集群还是主从，都需要申请对应的count组redis后端机器
        if ticket_type in cluster_ticket_type or ticket_type in single_ticket_type:
            # 为了保证每组master和slave都在不同机房，需要采用遍历方式申请
            for __ in range(0, group_count):
                temp = copy.deepcopy(self.common_param)
                temp["count"] = DBConstNumEnum.REDIS_ROLE_NUM
                temp["item"] = MediumEnum.Redis
                #  TODO 这个地方根据规格构建spec的其他参数，来寻找同等规格替代机器
                # temp['spec'] =
                temp["device_class"] = spec
                rms_detail.append(temp)

        # 只有集群才需要申请proxy、默认申请3台
        if ticket_type in cluster_ticket_type:
            temp = copy.deepcopy(self.common_param)
            temp["count"] = DBConstNumEnum.PROXY_DEFAULT_NUM
            temp["item"] = MediumEnum.Twemproxy
            temp["spec"] = self.proxy_spec
            temp["device_class"] = "S5.MEDIUM4"
            rms_detail.append(temp)
        return rms_detail

    @staticmethod
    def __post(post_params: Optional[Dict]):
        """
        定义post请求
        """
        return requests.post("https://todo.resource.pool", json=post_params).json()

    def get_nodes(self, post_details: list) -> Optional[List]:
        """
        锁定主机资源
        """

        resp = self.__post(
            {
                "api_version": RDMSApplyEnum.Version,
                "applyfor": "",
                "dry_run": False,
                "details": post_details,
            }
        )

        if resp["code"] != 0:
            logger.error(_(" 获取资源失败: {}").format(resp))
            return None

        return resp["data"]
