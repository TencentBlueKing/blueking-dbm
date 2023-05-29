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

from django.utils.translation import ugettext_lazy as _

from ..base import BaseApi
from ..domains import NAMESERVICE_APIGW_DOMAIN


class _NameServiceApi(BaseApi):
    MODULE = _("名字服务")
    BASE = NAMESERVICE_APIGW_DOMAIN

    def __init__(self):
        self.clb_create_lb_and_register_target = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/create_lb_and_register_target",
            description=_("创建clb并绑定后端主机"),
        )
        self.clb_deregister_part_target = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/deregister_part_target",
            description=_("clb解绑部分后端主机"),
        )
        self.clb_register_part_target = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/register_part_target",
            description=_("clb新增绑定部分后端主机"),
        )
        self.clb_get_target_private_ips = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/get_target_private_ips",
            description=_("获取已绑定clb的后端主机私网IP"),
        )
        self.clb_check_clb_register_target_by_ip = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/check_clb_register_target_by_ip",
            description=_("通过IP查询该IP是否已经被clb绑定了"),
        )
        self.clb_deregister_target_and_del_lb = self.generate_data_api(
            method="POST",
            url="/api/nameservice/clb/deregister_target_and_del_lb",
            description=_("解绑后端主机并删除clb"),
        )
        self.polaris_create_service_alias_and_bind_targets = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/create_service_alias_and_bind_targets",
            description=_("创建北极星服务和别名并绑定后端主机"),
        )
        self.polaris_unbind_part_targets = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/unbind_part_targets",
            description=_("北极星解绑部分后端主机"),
        )
        self.polaris_bind_part_targets = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/bind_part_targets",
            description=_("北极星新增绑定部分后端主机"),
        )
        self.polaris_describe_targets = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/describe_targets",
            description=_("获取北极星已绑定的后端主机信息"),
        )
        self.polaris_unbind_targets_and_delete_alias_service = self.generate_data_api(
            method="POST",
            url="/api/nameservice/polaris/unbind_targets_and_delete_alias_service",
            description=_("解绑后端主机并删除别名和北极星服务"),
        )


NameServiceApi = _NameServiceApi()
