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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

import backend.flow.utils.mysql.mysql_context_dataclass as flow_context
from backend.components import MySQLPrivManagerApi
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.flow.plugins.components.collections.common.base_service import BaseService


class CreateUserService(BaseService):
    """
    todo 后续需要传入bk_cloud_id
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        global_data = data.get_one_of_inputs("global_data")

        trans_data.master_access_slave_user = kwargs["user"]
        trans_data.master_access_slave_password = kwargs["psw"]
        data.outputs["trans_data"] = trans_data

        encrypted = AsymmetricHandler.encrypt_with_pubkey(
            pubkey=MySQLPrivManagerApi.fetch_public_key(), content=kwargs["psw"]
        )

        try:
            MySQLPrivManagerApi.add_priv_without_account_rule(
                params={
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                    "bk_biz_id": global_data["bk_biz_id"],
                    "operator": global_data["created_by"],
                    "user": kwargs["user"],
                    "psw": encrypted,
                    "hosts": kwargs["hosts"],
                    "dbname": kwargs["dbname"],
                    "dml_ddl_priv": kwargs["dml_ddl_priv"],
                    "global_priv": kwargs["global_priv"],
                    "address": kwargs["address"],
                }
            )
            self.log_info(_("在「{}」创建临时用户「{}@{}」成功").format(kwargs["address"], kwargs["user"], kwargs["hosts"]))
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("创建用户接口异常，相关信息: {}").format(e))
            return False

        return True


class CreateUserComponent(Component):
    name = __name__
    code = "mysql_create_user"
    bound_service = CreateUserService
