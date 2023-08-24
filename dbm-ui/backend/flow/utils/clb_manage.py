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
from backend.db_meta.models import CLBEntryDetail

logger = logging.getLogger("flow")


def GetClbByIp(clb_ip: str):
    clb_info = CLBEntryDetail.objects.filter(clb_ip=clb_ip).values()[0]
    return CLBManage(clb_info["clb_id"], clb_info["clb_ip"], clb_info["listener_id"], clb_info["clb_region"])


class CLBManage(object):
    """
    定义clb域名管理类
    目前服务部署模式：clb属于插件类接入工具，使用后，扩缩容等涉及到变更的操作，需要同步修改clb
    """

    def __init__(self, clb_id: str, clb_ip: str, listener_id: str, clb_region: str):
        self.clb_ip = clb_ip
        self.clb_id = clb_id
        self.listener_id = listener_id
        self.clb_region = clb_region

    def del_clb_rs(self, instance_list: list) -> bool:
        """
        删除clb后端的rs记录;适用场景：proxy下架的时候需要删除
        """
        NameServiceApi.clb_deregister_part_target(
            {
                "region": self.clb_region,
                "loadbalancerid": self.clb_id,
                "listenerid": self.listener_id,
                "ips": instance_list,
            },
            raw=True,
        )
        return True

    def add_clb_rs(self, instance_list: list) -> bool:
        """
        增加clb后端的rs记录;适用场景：proxy上架的时候需要新增
        """
        NameServiceApi.clb_register_part_target(
            {
                "region": self.clb_region,
                "loadbalancerid": self.clb_id,
                "listenerid": self.listener_id,
                "ips": instance_list,
            },
            raw=True,
        )
        return True

    def deregiste_clb(self) -> bool:
        """
        删除clb后端的rs记录，并删除clb；
        适用场景：集群下架
        """
        NameServiceApi.clb_deregister_target_and_del_lb(
            {
                "region": self.clb_region,
                "loadbalancerid": self.clb_id,
                "listenerid": self.listener_id,
            },
            raw=True,
        )
        return True
