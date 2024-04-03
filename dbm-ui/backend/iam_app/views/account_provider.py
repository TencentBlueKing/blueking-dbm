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

from backend.components import DBPrivManagerApi
from backend.components.base import DataAPI
from backend.db_services.dbpermission.constants import AccountType
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.views.iam_provider import BaseInterfaceResourceProvider

logger = logging.getLogger("root")


class AccountResourceProvider(BaseInterfaceResourceProvider):
    """
    账号资源的反向拉取类
    """

    api: DataAPI = DBPrivManagerApi.get_account
    resource_meta: ResourceMeta = None
    account_type: AccountType = None

    @staticmethod
    def convert_condition_field(condition):
        # 账号的业务参数要是整型
        condition["bk_biz_id"] = int(condition["bk_biz_id"])
        return condition

    def list_instance(self, filter, page, **options):
        filter.data_source = self.api
        filter.value_list = [self.resource_meta.lookup_field, *self.resource_meta.display_fields]
        filter.keyword_field = "user_like"
        filter.conditions = {"cluster_type": self.account_type}
        return super().list_instance(filter, page, **options)

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def fetch_instance_info(self, filter, **options):
        filter.data_source = self.api
        return super().fetch_instance_info(filter, **options)

    def list_instance_by_policy(self, filter, page, **options):
        key_mapping = {
            f"{self.resource_meta.id}.ids": "ids",
            f"{self.resource_meta.id}.id": "id",
            f"{self.resource_meta.id}._bk_iam_path_": "bk_biz_id",
        }
        values_hook = {"bk_biz_id": lambda value: value[1:-1].split(",")[1]}
        return self._list_instance_by_policy(
            data_source=self.api,
            value_list=["id", "user"],
            key_mapping=key_mapping,
            value_hooks=values_hook,
            filter=filter,
            page=page,
        )


class MySQLAccountResourceProvider(AccountResourceProvider):
    """
    mysql账号资源的反向拉取类
    """

    account_type = AccountType.MYSQL
    resource_meta = ResourceEnum.MYSQL_ACCOUNT


class SQLServerAccountResourceProvider(AccountResourceProvider):
    """
    mysql账号资源的反向拉取类
    """

    account_type = AccountType.SQLServer
    resource_meta = ResourceEnum.SQLSERVER_ACCOUNT


class MongoDBAccountResourceProvider(AccountResourceProvider):
    """
    mysql账号资源的反向拉取类
    """

    account_type = AccountType.MONGODB
    resource_meta = ResourceEnum.MONGODB_ACCOUNT


class TendbClusterAccountResourceProvider(AccountResourceProvider):
    """
    mysql账号资源的反向拉取类
    """

    account_type = AccountType.TENDBCLUSTER
    resource_meta = ResourceEnum.TENDBCLUSTER_ACCOUNT
