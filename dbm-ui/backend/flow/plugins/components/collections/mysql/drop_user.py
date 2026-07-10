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
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


def is_ignorable_drop_user_error(error_msg: str) -> bool:
    """用户不存在等场景视为可忽略。"""
    if not error_msg:
        return False
    lower = error_msg.lower()
    keywords = [
        "can't drop",
        "operation drop user failed",
        "unknown user",
        "does not exist",
        "1396",  # ERROR 1396 (HY000): Operation DROP USER failed
    ]
    return any(k in lower for k in keywords)


class DropUserService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        ignore_errors=True 时，用户不存在等错误仅告警不失败（DTS 清理等场景）
        """
        kwargs = data.get_one_of_inputs("kwargs")
        sql = "drop user `{}`@`{}`;".format(kwargs["user"], kwargs["host"])
        address = kwargs["address"]
        ignore_errors = kwargs.get("ignore_errors", False)

        try:
            resp = DRSApi.rpc(
                {
                    "addresses": [address],
                    "cmds": [sql],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )

            top_err = resp[0].get("error_msg") or ""
            cmd_err = ""
            if resp[0].get("cmd_results"):
                cmd_err = resp[0]["cmd_results"][0].get("error_msg") or ""
            err = top_err or cmd_err
            if err:
                if ignore_errors and is_ignorable_drop_user_error(err):
                    self.log_warning(_("忽略删除临时用户失败 {}@{}@{}: {}").format(kwargs["user"], kwargs["host"], address, err))
                    return True
                if top_err:
                    self.log_error(_("在「{}」执行sql失败，相关信息: {}").format(address, top_err))
                else:
                    self.log_error(
                        _("在「{}」执行sql{}失败，相关信息: {}").format(address, resp[0]["cmd_results"][0]["cmd"], cmd_err)
                    )
                return False

        except Exception as e:  # pylint: disable=broad-except
            # 与 SQL 错误分支对齐：仅「用户不存在」类可忽略，网络/权限等仍失败
            if ignore_errors and is_ignorable_drop_user_error(str(e)):
                self.log_warning(_("忽略删除临时用户失败 {}@{}@{}: {}").format(kwargs["user"], kwargs["host"], address, e))
                return True
            self.log_error(_("删除用户接口异常，相关信息: {}").format(e))
            return False

        self.log_info(_("在「{}」删除临时用户「{}@{}」成功").format(address, kwargs["user"], kwargs["host"]))
        return True


class DropUserComponent(Component):
    name = __name__
    code = "mysql_drop_user"
    bound_service = DropUserService
