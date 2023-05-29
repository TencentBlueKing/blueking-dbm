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
import itertools
import logging
from typing import Any, List, Tuple

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components.mysql_priv_manager.client import MySQLPrivManagerApi
from backend.db_services.mysql.permission.authorize.models import MySQLAuthorizeRecord
from backend.exceptions import ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class AuthorizeRules(BaseService):
    """根据定义的用户规则模板进行授权"""

    def _execute(self, data, parent_data, callback=None) -> bool:

        # kwargs就是调用授权接口传入的参数
        kwargs = data.get_one_of_inputs("kwargs")
        ticket_id = kwargs["uid"]
        ticket_type = kwargs["ticket_type"]
        bk_biz_id = kwargs["bk_biz_id"]
        authorize_data_list = kwargs["rules_set"]
        authorize_success_count = 0

        for authorize_data in authorize_data_list:
            # 将授权信息存入record
            access_dbs = [account_rule["dbname"] for account_rule in authorize_data["account_rules"]]
            record = MySQLAuthorizeRecord(
                ticket_id=ticket_id,
                user=authorize_data["user"],
                source_ips="\n".join(authorize_data["source_ips"]),
                target_instances="\n".join(authorize_data["target_instances"]),
                access_dbs="\n".join(access_dbs),
            )

            # 生成当前规则的描述细则
            rules_product: List[Tuple[Any, ...]] = list(
                itertools.product(
                    [authorize_data["user"]],
                    access_dbs,
                    [", ".join(authorize_data["source_ips"])],
                    authorize_data["target_instances"],
                )
            )
            rules_description: str = "\n".join(
                [
                    _("{}. 账号规则: {}-{}, 来源ip: {}, 目标集群: {}").format(index + 1, rule[0], rule[1], rule[2], rule[3])
                    for index, rule in enumerate(rules_product)
                ]
            )

            # 进行授权，无论授权是否成功，都需要将message存入record中
            self.log_info(_("授权规则明细:\n{}\n").format(rules_description))
            try:
                resp = MySQLPrivManagerApi.authorize_rules(params=authorize_data, raw=True)

                record.status = int(resp["code"]) == 0
                authorize_success_count += record.status

                record.error = resp["message"]
                self.log_info(f"{resp['message']}\n")

            except Exception as e:  # pylint: disable=broad-except
                record.status = False
                if isinstance(e, ApiResultError):
                    error_message = _("「授权接口返回结果异常」{}").format(e.message)
                else:
                    error_message = _("「授权接口调用异常」{}").format(e)

                record.error = error_message
                self.log_error(_("授权异常，相关信息: {}\n").format(error_message))

            record.save()

        # 授权结果汇总
        overall_result = authorize_success_count == len(authorize_data_list)
        overall_result_alias = _("成功") if overall_result else _("失败")
        self.log_info(_("授权整体结果{}").format(overall_result_alias))

        if ticket_type == TicketType.MYSQL_EXCEL_AUTHORIZE_RULES:
            self.log_info(
                _("Excel导入授权行数:{}，成功授权数目:{}，失败授权数目:{}").format(
                    len(authorize_data_list),
                    authorize_success_count,
                    len(authorize_data_list) - authorize_success_count,
                )
            )

        self.log_info(
            _(
                "授权结果详情请下载excel: <a href='{}/apis/mysql/bizs/{}/permission/authorize/"
                "get_authorize_info_excel/?ticket_id={}'>excel 下载</a>"
            ).format(env.BK_SAAS_HOST, bk_biz_id, ticket_id)
        )
        return overall_result

    def inputs_format(self) -> List:
        return [Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True)]


class AuthorizeRulesComponent(Component):
    name = __name__
    code = "authorize_rules"
    bound_service = AuthorizeRules
