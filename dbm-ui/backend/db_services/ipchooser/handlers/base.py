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
import typing

from backend.components import CCApi

from .. import constants, types
from ..constants import BK_OS_CODE__TYPE
from ..query import resource


class BaseHandler:
    @staticmethod
    def get_meta_data(bk_biz_id: int) -> types.MetaData:
        return {"scope_type": constants.ScopeType.BIZ.value, "scope_id": str(bk_biz_id), "bk_biz_id": bk_biz_id}

    @classmethod
    def format_hosts(cls, hosts: typing.List[types.HostInfo], bk_biz_id: int) -> typing.List[types.FormatHostInfo]:
        """
        格式化主机信息
        :param hosts: 尚未进行格式化处理的主机信息
        :return: 格式化后的主机列表
        """
        biz_id__info_map: typing.Dict[int, typing.Dict] = {
            biz_info["bk_biz_id"]: biz_info for biz_info in resource.ResourceQueryHelper.fetch_biz_list()
        }

        # TODO: 暂不支持 >1000
        resp = CCApi.search_cloud_area({"page": {"start": 0, "limit": 1000}}, use_admin=True)

        if resp.get("info"):
            cloud_id__info_map: typing.Dict[int, typing.Dict] = {
                cloud_info["bk_cloud_id"]: cloud_info["bk_cloud_name"] for cloud_info in resp["info"]
            }
        else:
            # 默认存在直连区域
            cloud_id__info_map = {
                constants.DEFAULT_CLOUD: {
                    "bk_cloud_id": constants.DEFAULT_CLOUD,
                    "bk_cloud_name": constants.DEFAULT_CLOUD_NAME,
                }
            }

        formatted_hosts: typing.List[types.HostInfo] = []
        for host in hosts:
            bk_cloud_id = host["bk_cloud_id"]
            formatted_hosts.append(
                {
                    "meta": BaseHandler.get_meta_data(bk_biz_id),
                    "host_id": host["bk_host_id"],
                    "ip": host["bk_host_innerip"],
                    "ipv6": host.get("bk_host_innerip_v6", ""),
                    "bk_host_outerip": host.get("bk_host_outerip", ""),
                    "cloud_id": host["bk_cloud_id"],
                    "cloud_vendor": host.get("bk_cloud_vendor", ""),
                    "agent_id": host.get("bk_agent_id", ""),
                    "host_name": host.get("bk_host_name", ""),
                    "os_name": host.get("bk_os_type", ""),
                    "os_type": BK_OS_CODE__TYPE.get(host.get("bk_os_type", ""), ""),
                    "alive": host.get("status"),
                    "cloud_area": {
                        "id": bk_cloud_id,
                        "name": cloud_id__info_map.get(bk_cloud_id, bk_cloud_id),
                    },
                    "biz": {
                        "id": bk_biz_id,
                        "name": biz_id__info_map.get(bk_biz_id, {}).get("bk_biz_name", bk_biz_id),
                    },
                    # 暂不需要的字段，留作扩展
                    "bk_mem": host.get("bk_mem"),
                    "bk_disk": host.get("bk_disk"),
                    "bk_cpu": host.get("bk_cpu"),
                    "bk_idc_name": host.get("idc_city_name"),
                    "bk_idc_id": host.get("idc_city_id"),
                    # "bk_cpu_architecture": host["bk_cpu_architecture"],
                    # "bk_cpu_module": host["bk_cpu_module"],
                }
            )

        return formatted_hosts

    @classmethod
    def format_host_id_infos(
        cls, hosts: typing.List[types.HostInfo], bk_biz_id: int
    ) -> typing.List[types.FormatHostInfo]:
        """
        格式化主机信息
        :param hosts: 尚未进行格式化处理的主机信息
        :return: 格式化后的主机列表
        """

        formatted_hosts: typing.List[types.HostInfo] = []
        for host in hosts:
            formatted_hosts.append(
                {
                    "meta": BaseHandler.get_meta_data(bk_biz_id),
                    "host_id": host["bk_host_id"],
                    "ip": host["bk_host_innerip"],
                    "ipv6": host.get("bk_host_innerip_v6"),
                    "cloud_id": host["bk_cloud_id"],
                }
            )

        return formatted_hosts
