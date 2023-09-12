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

from ..base import DataAPI
from ..domains import MYSQL_PRIV_MANAGER_APIGW_DOMAIN


class _MySQLPrivManagerApi(object):

    MODULE = _("MySQL权限管理")

    def __init__(self):
        # 账号规则相关
        self.account_rule_detail = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/get_account_rule_detail",
            module=self.MODULE,
            description=_("帐号规则详情"),
        )
        self.list_account_rules = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/get_account_rule_list",
            module=self.MODULE,
            description=_("帐号规则清单"),
        )
        self.add_account_rule = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/add_account_rule",
            module=self.MODULE,
            description=_("添加帐号规则"),
        )
        self.delete_account_rule = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/delete_account_rule",
            module=self.MODULE,
            description=_("删除帐号规则"),
        )
        self.modify_account_rule = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/modify_account_rule",
            module=self.MODULE,
            description=_("修改帐号规则"),
        )

        self.fetch_public_key = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/pub_key",
            module=self.MODULE,
            description=_("请求公钥"),
        )
        self.create_account = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/add_account",
            module=self.MODULE,
            description=_("创建账号"),
        )
        self.delete_account = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/delete_account",
            module=self.MODULE,
            description=_("删除账号"),
        )
        self.update_password = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/modify_account",
            module=self.MODULE,
            description=_("修改账号的密码"),
        )

        # 授权规则相关
        self.pre_check_authorize_rules = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/add_priv_dry_run",
            module=self.MODULE,
            description=_("前置检查授权数据"),
        )
        self.authorize_rules = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/add_priv",
            module=self.MODULE,
            description=_("添加授权"),
        )
        self.get_online_rules = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/get_online_rules",
            module=self.MODULE,
            description=_("查询现网授权记录"),
        )

        # 权限克隆相关
        self.clone_instance = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/clone_instance_priv",
            module=self.MODULE,
            description=_("实例间权限克隆"),
        )
        self.pre_check_clone_instance = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/clone_instance_priv_dry_run",
            module=self.MODULE,
            description=_("实例间权限克隆前置检查"),
        )
        self.clone_client = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/clone_client_priv",
            module=self.MODULE,
            description=_("客户端权限克隆"),
        )
        self.pre_check_clone_client = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/clone_client_priv_dry_run",
            module=self.MODULE,
            description=_("客户端权限克隆前置检查"),
        )
        self.add_priv_without_account_rule = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/add_priv_without_account_rule",
            module=self.MODULE,
            description=_("mysql实例创建临时账号(切换专属接口)"),
        )
        self.modify_mysql_admin_password = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/modify_mysql_admin_password",
            module=self.MODULE,
            description=_("新增或者修改mysql实例中管理用户的密码"),
        )
        self.get_password = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/get_password",
            module=self.MODULE,
            description=_("获取密码"),
        )
        self.modify_password = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/modify_password",
            module=self.MODULE,
            description=_("新增或者修改密码"),
        )
        self.get_random_string = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/get_random_string",
            module=self.MODULE,
            description=_("生成随机字符串"),
        )
        self.get_security_rule = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/get_security_rule",
            module=self.MODULE,
            description=_("获取安全规则"),
        )
        self.add_security_rule = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/add_security_rule",
            module=self.MODULE,
            description=_("添加安全规则"),
        )
        self.modify_security_rule = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/modify_security_rule",
            module=self.MODULE,
            description=_("修改安全规则"),
        )
        self.delete_security_rule = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/delete_security_rule",
            module=self.MODULE,
            description=_("删除安全规则"),
        )
        self.get_randomize_exclude = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/get_randomize_exclude",
            module=self.MODULE,
            description=_("获取不参与随机化的业务"),
        )
        self.modify_randomize_exclude = (
            DataAPI(
                method="POST",
                base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
                url="/priv/modify_randomize_exclude",
                module=self.MODULE,
                description=_("修改不参与随机化的业务"),
            ),
        )
        self.check_password = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/check_password",
            module=self.MODULE,
            description=_("校验密码强度"),
        )
        self.get_mysql_admin_password = DataAPI(
            method="POST",
            base=MYSQL_PRIV_MANAGER_APIGW_DOMAIN,
            url="/priv/get_mysql_admin_password",
            module=self.MODULE,
            description=_("获取mysql ADMIN的密码——mysql专用"),
        )


MySQLPrivManagerApi = _MySQLPrivManagerApi()
