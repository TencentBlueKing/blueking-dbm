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
from ..domains import MYSQL_PRIV_MANAGER_APIGW_DOMAIN


class _DBPrivManagerApi(BaseApi):
    MODULE = _("DB权限管理")
    BASE = MYSQL_PRIV_MANAGER_APIGW_DOMAIN

    def __init__(self):
        # 账号规则相关
        self.account_rule_detail = self.generate_data_api(
            method="POST",
            url="/priv/get_account_rule_detail",
            description=_("帐号规则详情"),
        )
        self.list_account_rules = self.generate_data_api(
            method="POST",
            url="/priv/get_account_rule_list",
            description=_("帐号规则清单"),
        )
        self.add_account_rule = self.generate_data_api(
            method="POST",
            url="/priv/add_account_rule",
            description=_("添加帐号规则"),
        )
        self.delete_account_rule = self.generate_data_api(
            method="POST",
            url="/priv/delete_account_rule",
            description=_("删除帐号规则"),
        )
        self.modify_account_rule = self.generate_data_api(
            method="POST",
            url="/priv/modify_account_rule",
            description=_("修改帐号规则"),
        )

        self.fetch_public_key = self.generate_data_api(
            method="POST",
            url="/priv/pub_key",
            description=_("请求公钥"),
        )
        self.create_account = self.generate_data_api(
            method="POST",
            url="/priv/add_account",
            description=_("创建账号"),
        )
        self.delete_account = self.generate_data_api(
            method="POST",
            url="/priv/delete_account",
            description=_("删除账号"),
        )
        self.update_password = self.generate_data_api(
            method="POST",
            url="/priv/modify_account",
            description=_("修改账号的密码"),
        )

        # 授权规则相关
        self.pre_check_authorize_rules = self.generate_data_api(
            method="POST",
            url="/priv/add_priv_dry_run",
            description=_("前置检查授权数据"),
        )
        self.authorize_rules = self.generate_data_api(
            method="POST",
            url="/priv/add_priv",
            description=_("添加授权"),
        )
        self.get_online_rules = self.generate_data_api(
            method="POST",
            url="/priv/get_online_rules",
            description=_("查询现网授权记录"),
        )

        # 权限克隆相关
        self.clone_instance = self.generate_data_api(
            method="POST",
            url="/priv/clone_instance_priv",
            description=_("实例间权限克隆"),
        )
        self.pre_check_clone_instance = self.generate_data_api(
            method="POST",
            url="/priv/clone_instance_priv_dry_run",
            description=_("实例间权限克隆前置检查"),
        )
        self.clone_client = self.generate_data_api(
            method="POST",
            url="/priv/clone_client_priv",
            description=_("客户端权限克隆"),
        )
        self.pre_check_clone_client = self.generate_data_api(
            method="POST",
            url="/priv/clone_client_priv_dry_run",
            description=_("客户端权限克隆前置检查"),
        )
        self.add_priv_without_account_rule = self.generate_data_api(
            method="POST",
            url="/priv/add_priv_without_account_rule",
            description=_("mysql实例创建临时账号(切换专属接口)"),
        )
        self.modify_admin_password = self.generate_data_api(
            method="POST",
            url="/priv/modify_admin_password",
            description=_("新增或者修改实例中管理用户的密码"),
        )
        self.get_password = self.generate_data_api(
            method="POST",
            url="/priv/get_password",
            description=_("获取密码"),
        )
        self.modify_password = self.generate_data_api(
            method="POST",
            url="/priv/modify_password",
            description=_("新增或者修改密码"),
        )
        self.get_random_string = self.generate_data_api(
            method="POST",
            url="/priv/get_random_string",
            description=_("生成随机字符串"),
        )
        self.get_security_rule = self.generate_data_api(
            method="POST",
            url="/priv/get_security_rule",
            description=_("获取安全规则"),
        )
        self.add_security_rule = self.generate_data_api(
            method="POST",
            url="/priv/add_security_rule",
            description=_("添加安全规则"),
        )
        self.modify_security_rule = self.generate_data_api(
            method="POST",
            url="/priv/modify_security_rule",
            description=_("修改安全规则"),
        )
        self.delete_security_rule = self.generate_data_api(
            method="POST",
            url="/priv/delete_security_rule",
            description=_("删除安全规则"),
        )
        self.get_randomize_exclude = self.generate_data_api(
            method="POST",
            url="/priv/get_randomize_exclude",
            description=_("获取不参与随机化的业务"),
        )
        self.modify_randomize_exclude = self.generate_data_api(
            method="POST",
            url="/priv/modify_randomize_exclude",
            description=_("修改不参与随机化的业务"),
        )
        self.check_password = self.generate_data_api(
            method="POST",
            url="/priv/check_password",
            description=_("校验密码强度"),
        )
        self.get_mysql_admin_password = self.generate_data_api(
            method="POST",
            url="/priv/get_mysql_admin_password",
            description=_("获取mysql ADMIN的密码——mysql专用"),
        )
        self.delete_password = self.generate_data_api(
            method="POST",
            url="/priv/delete_password",
            description=_("删除实例密码记录"),
        )
        self.get_account_include_password = self.generate_data_api(
            method="POST",
            url="/priv/get_account_include_psw",
            description=_("查询账号和密码信息"),
        )


# 历史原因，最先只对mysql进行权限操作，所以命名为MySQLPrivManagerApi。但是现在统一作为所有组件的权限操作
DBPrivManagerApi = _DBPrivManagerApi()
