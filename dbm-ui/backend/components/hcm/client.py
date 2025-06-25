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

from django.utils.translation import gettext_lazy as _

from ... import env
from .. import CCApi
from ..base import BaseApi
from ..domains import HCM_APIGW_DOMAIN


class _HCMApi(BaseApi):
    MODULE = _("HCM海垒 服务")
    BASE = HCM_APIGW_DOMAIN

    def __init__(self):
        self.list_cvm_device = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/config/findmany/config/cvm/device/detail/",
            description=_("获取可用的CVM机型"),
        )
        self.dissolve_check = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/dissolve/hosts/status/check/",
            description=_("查询主机是否为待裁撤阶段"),
        )
        self.uwork_check = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/task/hosts/uwork_tickets/status/check/",
            description=_("检查主机是否有未完结的uwork单据"),
        )
        self.create_biz_recycle = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/task/create/recycle/order",
            description=_("创建业务下的资源回收单据"),
        )

    def check_host_is_dissolved(self, bk_host_ids: list):
        if not HCM_APIGW_DOMAIN or not bk_host_ids:
            return []

        # 查询主机的业务信息，这里查询的主机要求为统一业务(暂不做校验)
        biz = CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids[:1]}, use_admin=True)[0]["bk_biz_id"]
        # 查询裁撤主机列表
        resp = self.dissolve_check(params={"bk_biz_id": biz, "bk_host_ids": bk_host_ids}, use_admin=True)
        dissolved_hosts = [d["bk_host_id"] for d in resp["info"] if d["status"]]
        return dissolved_hosts

    def check_host_has_uwork(self, bk_host_ids: list):
        if not HCM_APIGW_DOMAIN or not bk_host_ids:
            return {}

        has_uwork_hosts_map = {}
        # 查询主机的业务信息，这里查询的主机要求为统一业务(暂不做校验)
        biz = CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids[:1]}, use_admin=True)[0]["bk_biz_id"]

        def __check_uwork(check_host_ids):
            # 查询包含uwork主机列表
            resp = self.uwork_check(params={"bk_biz_id": biz, "bk_host_ids": check_host_ids}, use_admin=True)
            has_uwork_hosts_map.update({d["bk_host_id"]: d for d in resp["details"] if d["has_open_tickets"]})

        # hcm 一次校验不能超过100，这里分批次校验，考虑下架大量机器的情况较少，这里直接串行提交
        batch = 90
        for index in range(0, len(bk_host_ids), batch):
            __check_uwork(bk_host_ids[index : index + batch])

        return has_uwork_hosts_map

    def create_recycle(self, bk_host_ids: list):
        params = {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "bk_host_ids": bk_host_ids,
            "remark": "dbm auto create",
            # 回收策略固定是：立刻销毁
            "return_plan": {"cvm": "IMMEDIATE", "pm": "IMMEDIATE"},
        }
        resp = self.create_biz_recycle(params=params)
        return resp["info"][0]["order_id"]


HCMApi = _HCMApi()
