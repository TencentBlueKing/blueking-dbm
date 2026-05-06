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
from backend.components import DBPrivManagerApi
from backend.db_meta.enums import ClusterType
from backend.db_services.dbpermission.db_account.handlers import AccountHandler


def show_biz_mysql_privilege_template(bk_biz_id: int, cluster_type: ClusterType):
    account_type = ClusterType.cluster_type_to_db_type(cluster_type)

    priv_res = DBPrivManagerApi.get_account(params={"cluster_type": account_type, "bk_biz_id": bk_biz_id})

    user_info_map = {user["user"]: user for user in priv_res["results"]}

    user_db_map = AccountHandler.aggregate_user_db_rules(bk_biz_id, account_type)

    res = []
    for account_name in user_info_map.keys():
        account_detail = []
        for dbname, privileges in user_db_map.get(account_name, {}).items():
            account_detail.append({"dbname": dbname, "privileges": privileges})

        res.append({"account_name": account_name, "db_privileges": account_detail})

    return res
