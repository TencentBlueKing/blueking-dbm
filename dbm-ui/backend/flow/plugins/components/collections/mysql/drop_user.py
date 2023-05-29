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

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class DropUserService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        sql = "drop user `{}`@`{}`;".format(kwargs["user"], kwargs["host"])
        address = kwargs["address"]

        try:
            resp = DRSApi.rpc(
                {
                    "addresses": [address],
                    "cmds": [sql],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )

            if resp[0]["error_msg"]:
                self.log_error(_("在「{}」执行sql失败，相关信息: {}").format(address, resp[0]["error_msg"]))
                return False
            elif resp[0]["cmd_results"][0]["error_msg"]:
                self.log_error(
                    _("在「{}」执行sql{}失败，相关信息: {}").format(
                        address, resp[0]["cmd_results"][0]["cmd"], resp[0]["cmd_results"][0]["error_msg"]
                    )
                )
                return False

        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("删除用户接口异常，相关信息: {}").format(e))
            return False

        self.log_info(_("在「{}」删除临时用户「{}@{}」成功").format(address, kwargs["user"], kwargs["host"]))
        return True


class DropUserComponent(Component):
    name = __name__
    code = "mysql_drop_user"
    bound_service = DropUserService
