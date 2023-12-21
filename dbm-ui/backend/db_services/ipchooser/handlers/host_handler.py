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
from ..constants import ModeType
from ..query.resource import ResourceQueryHelper
from .base import BaseHandler


class HostHandler:
    @staticmethod
    def details_base(
        scope_list: types.ScopeList,
        host_property_filter: typing.Dict,
        mode: str = ModeType.ALL.value,
    ) -> typing.List[types.FormatHostInfo]:
        """
        获取主机详情
        :param scope_list: 资源范围数组
        :param host_property_filter: 主机查询条件
        :param mode: all（全部）/idle_only（空闲机）
        :return:
        """

        # 不支持多业务同时查询
        biz_scope = [scope["bk_biz_id"] for scope in scope_list]
        bk_biz_id = biz_scope[0]

        # 查询主机
        params = {
            "bk_biz_id": bk_biz_id,
            "fields": [
                "bk_host_id",
                "bk_agent_id",
                "bk_host_name",
                "bk_os_type",
                "bk_host_innerip",
                "bk_host_innerip_v6",
                "bk_cloud_id",
                "idc_name",
                "bk_mem",
                "bk_cpu",
                "bk_disk",
                "bk_host_outerip",
                "idc_city_id",
                "idc_city_name",
            ],
            "host_property_filter": host_property_filter,
            # TODO: 搜到的条数大于1000，需要循环查询，该接口当前协议不做分页，可能需要循环查询
            "page": {"start": 0, "limit": 1000, "sort": "bk_host_id"},
        }

        if mode == constants.ModeType.IDLE_ONLY.value:
            _, idle_module_id = ResourceQueryHelper.get_idle_set_module(bk_biz_id)
            params.update(
                {
                    "bk_module_ids": [idle_module_id],
                }
            )

        # 获取主机信息
        resp = CCApi.list_biz_hosts(params, use_admin=True)
        hosts = resp["info"]

        ResourceQueryHelper.fill_agent_status(hosts)

        return BaseHandler.format_hosts(hosts, bk_biz_id)

    @classmethod
    def check(
        cls,
        scope_list: types.ScopeList,
        ip_list: typing.List[str],
        ipv6_list: typing.List[str],
        key_list: typing.List[str],
        mode: str = ModeType.ALL.value,
    ) -> typing.List[types.FormatHostInfo]:
        """
        根据输入的`IP`/`IPv6`/`主机名`/`host_id`等关键字信息获取真实存在的机器信息。
        :param scope_list: 资源范围数组
        :param ip_list: IPv4 列表
        :param ipv6_list: IPv6 列表
        :param key_list: 关键字列表
        :param mode: all（全部）/idle_only（空闲机）
        :return:
        """
        if not scope_list:
            return []

        inner_ip_set: typing.Set[str] = set()
        bk_host_id_set: typing.Set[int] = set()
        bk_host_name_set: typing.Set[str] = set()
        cloud_inner_ip_set: typing.Set[str] = set()

        # 获取bk_biz_id
        host_filter_cloud_id: typing.int = None
        if scope_list and "bk_cloud_id" in scope_list[0].keys():
            host_filter_cloud_id = scope_list[0]["bk_cloud_id"]

        for ip_or_cloud_ip in ip_list:
            # 按分隔符切割，获取切割后长度
            block_num: int = len(ip_or_cloud_ip.split(constants.CommonEnum.SEP.value, 1))
            # 默认按照host_filter_cloud_id过滤主机云区域，否则按照用户输入过滤
            if host_filter_cloud_id is None:
                # 长度为 1 表示单 IP，否则认为是 cloud_id:ip
                if block_num == 1:
                    inner_ip_set.add(ip_or_cloud_ip)
                else:
                    cloud_inner_ip_set.add(ip_or_cloud_ip)
            else:
                ip = ip_or_cloud_ip.split(constants.CommonEnum.SEP.value)[block_num - 1]
                cloud_inner_ip_set.add(f"{host_filter_cloud_id}{constants.CommonEnum.SEP.value}{ip}")

        for key in key_list:
            # 尝试将关键字解析为主机 ID
            try:
                bk_host_id_set.add(int(key))
            except ValueError:
                pass
            bk_host_name_set.add(key)

        # 构造逻辑或查询条件
        cloud_ip_rules = []
        for cloud_inner_ip in cloud_inner_ip_set:
            cloud_id, inner_ip = cloud_inner_ip.split(constants.CommonEnum.SEP.value, 1)
            cloud_ip_rules.append(
                {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_host_innerip", "operator": "equal", "value": inner_ip},
                        {"field": "bk_cloud_id", "operator": "equal", "value": int(cloud_id)},
                    ],
                }
            )

        # 构建主机过滤器
        host_property_filter = {
            "condition": "OR",
            "rules": [
                {"field": "bk_host_id", "operator": "in", "value": list(bk_host_id_set)},
                {"field": "bk_host_innerip", "operator": "in", "value": list(inner_ip_set)},
                {"field": "bk_host_innerip_v6", "operator": "in", "value": ipv6_list},
                {"field": "bk_host_name", "operator": "in", "value": list(bk_host_name_set)},
            ]
            + cloud_ip_rules,
        }
        return cls.details_base(scope_list, host_property_filter, mode)

    @classmethod
    def details(
        cls,
        scope_list: types.ScopeList,
        host_list: typing.List[types.FormatHostInfo],
        mode: str = ModeType.ALL.value,
    ) -> typing.List[types.FormatHostInfo]:
        """
        根据主机关键信息获取机器详情信息
        :param scope_list: 资源范围数组
        :param host_list: 主机关键信息列表
        :param mode: all（全部）/idle_only（空闲机）
        :return:
        """

        rules = []
        for host_info in host_list:
            if "host_id" in host_info:
                rule = {"field": "bk_host_id", "operator": "equal", "value": host_info["host_id"]}
            else:
                rule = {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_host_innerip", "operator": "equal", "value": host_info["ip"]},
                        {"field": "bk_cloud_id", "operator": "equal", "value": host_info["cloud_id"]},
                    ],
                }
            rules.append(rule)

        return cls.details_base(scope_list, {"condition": "OR", "rules": rules}, mode)
