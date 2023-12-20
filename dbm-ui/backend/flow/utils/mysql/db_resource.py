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

from backend.flow.consts import MediumEnum, RDMSApplyEnum
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")
single_ticket_type = [TicketType.MYSQL_SINGLE_APPLY.name]
ha_ticket_type = [TicketType.MYSQL_HA_APPLY.name]


class DBResource(object):
    """
    构建DB资源的类
    """

    def __init__(self):
        # self.temp_spec = {"cpu": [2], "ram": [3000], "hdd": [0], "ssd": [100]}
        self.mysql_spec = {"cpu": [1, 16], "ram": [1000, 30000], "hdd": [0, 1000], "ssd": [0]}
        self.proxy_spec = {"cpu": [1, 16], "ram": [1000, 30000], "hdd": [0, 1000], "ssd": [0]}
        self.common_param = {
            "count": 0,
            "location_spec": {
                "city": "{city}",
                "cross_switch": True,
                # "anti-affinity": "SAME_ZONE",  # 表示申请的机器必须是同园区。默认是跨园区，本地测试来用的
            },
            "spec": {},
            "allowBareMetaToDocker": True,
            "device_class": "{spec}",
            "item": "default",
        }

    def get_payload_params(self, city: str, cross_switch: bool, spec: str, ticket_type: str) -> Optional[List]:
        """
        根据单据类型，拼接对应的请求资源参数体
        """
        rms_detail = []
        self.common_param["location_spec"]["city"] = city
        self.common_param["location_spec"]["cross_switch"] = cross_switch
        self.common_param["device_class"] = spec

        if ticket_type in single_ticket_type:
            # 拼接部署一台单节点mysql集群的资源需求
            temp = copy.deepcopy(self.common_param)
            temp["count"] = 1
            temp["item"] = MediumEnum.MySQL
            temp["spec"] = self.mysql_spec
            rms_detail.append(temp)
            return rms_detail

        elif ticket_type in ha_ticket_type:
            # 拼接部署一套主从版mysql集群的资源需求
            for db_type in [MediumEnum.MySQL, MediumEnum.MySQLProxy]:
                temp = copy.deepcopy(self.common_param)
                temp["count"] = 2
                temp["item"] = db_type
                temp["spec"] = self.mysql_spec if db_type == MediumEnum.MySQL else self.proxy_spec
                # temp['device_class'] = 'S5t.SMALL2' if db_type == MediumEnum.MySQLProxy else spec
                # TODO 本地测试需要的，临时让所以机器规格都一致，方便测试，后续接入资源池再做调整
                temp["device_class"] = spec
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
        返回数据：
        [
            {'item': 'mysql', 'data': [{'ip': '127.0.0.1'}, ......]},
            {'item': 'mysql-proxy', 'data': [{'ip': '127.0.0.2'}, ......]}
        ]
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
