# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
import hashlib
import hmac
import time
from datetime import timedelta
from typing import Dict

from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.components.base import BaseApi
from backend.components.domains import XWORK_APIGW_DOMAIN
from backend.utils.time import timestamp2datetime


class _XworkApi(BaseApi):
    MODULE = _("Xwork 服务")
    BASE = XWORK_APIGW_DOMAIN

    # 待授权/已预约/处理中
    XWORK_UNFINISHED_CODE = [4, 5, 6]
    # 已结束/已避免/已取消
    XWORK_FINISHED_CODE = [7, 8, 9]

    def __init__(self):
        self.xwork_list = self.generate_data_api(
            method="POST",
            url="/fault_task/search",
            description=_("【查询】故障告警数据接口"),
        )

    @staticmethod
    def __generate_signature():
        """生成请求签名"""
        now = int(time.time())
        caller_key = bytes(env.XWORK_CALLER_KEY, encoding="utf8")
        hd_str = (str(now)).encode("utf-8")
        signature = hmac.new(caller_key, hd_str, digestmod=hashlib.sha512).hexdigest()
        return now, signature

    def check_xwork_list(self, host_ip_map: Dict[str, int]):
        """
        检查主机是否有xwork单据
        @param host_ip_map: 主机ip和主机ID的映射
        """
        if not XWORK_APIGW_DOMAIN or not host_ip_map:
            return {}

        # 查询xwork单据，默认查询一年以内
        now, signature = self.__generate_signature()
        end_time = timestamp2datetime(now)
        start_time = end_time - timedelta(days=365)
        params = {
            "CallerName": env.XWORK_CALLER_USER,
            "Authorization": {"TimeStamp": now, "Signature": signature},
            "ServiceParam": {
                "Filters": {
                    "BsiIp": list(host_ip_map.keys()),
                    "TaskStatusList": self.XWORK_UNFINISHED_CODE,
                    "SearchStartTime": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "SearchEndTime": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            },
            "Order": {},
            "Offset": 0,
            "Limit": len(host_ip_map),
        }
        data = self.xwork_list(params, raw=True)["ServiceResult"]["Data"]
        # 映射xwork与host
        has_xwork_hosts_map = {host_ip_map[d["BsiIp"]]: d for d in data}
        return has_xwork_hosts_map


XworkApi = _XworkApi()
