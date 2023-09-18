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

from backend.components import NameServiceApi
from backend.db_meta.models import PolarisEntryDetail

logger = logging.getLogger("flow")


def GetPolarisManageByName(servicename: str):
    polaris_info = PolarisEntryDetail.objects.filter(polaris_name=servicename).values()[0]
    return PolarisManage(
        polaris_info["polaris_name"],
        polaris_info["polaris_token"],
        polaris_info["polaris_l5"],
        polaris_info["alias_token"],
    )


class PolarisManage(object):
    """
    定义polaris域名管理类
    """

    def __init__(self, servicename: str, servicetoken: str, alias: str, aliastoken: str):
        self.servicename = servicename
        self.servicetoken = servicetoken
        self.alias = alias
        self.aliastoken = aliastoken

    def del_polaris_rs(self, instance_list: list) -> bool:
        """
        删除polaris后端的rs记录;适用场景：proxy下架的时候需要删除
        """
        NameServiceApi.polaris_unbind_part_targets(
            {"servicename": self.servicename, "servicetoken": self.servicetoken, "ips": instance_list},
            raw=True,
        )
        return True

    def add_polaris_rs(self, instance_list: list) -> bool:
        """
        增加polaris后端的rs记录;适用场景：proxy上架的时候需要新增
        """
        NameServiceApi.polaris_bind_part_targets(
            {"servicename": self.servicename, "servicetoken": self.servicetoken, "ips": instance_list},
            raw=True,
        )
        return True

    def deregiste_polaris(self) -> bool:
        """
        删除polaris后端rs记录，并删除polaris;适用场景：集群下架
        """
        NameServiceApi.polaris_unbind_targets_and_delete_alias_service(
            {
                "servicename": self.servicename,
                "servicetoken": self.servicetoken,
                "alias": self.alias,
                "aliastoken": self.aliastoken,
            },
            raw=True,
        )
        return True
