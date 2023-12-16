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
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.db_services.mysql.permission.clone.handlers import CloneHandler
from backend.db_services.mysql.permission.clone.models import MySQLPermissionCloneRecord
from backend.db_services.mysql.permission.constants import CloneType
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class CloneRules(BaseService):
    """根据克隆表单数据进行权限克隆"""

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        ticket_id = kwargs["uid"]
        bk_biz_id = kwargs["bk_biz_id"]
        operator = kwargs["created_by"]
        clone_type = kwargs["clone_type"]
        clone_cluster_type = kwargs["clone_cluster_type"]
        clone_data_list = kwargs["clone_data"]
        clone_success_count = 0

        # 如果是实例克隆，则提前获得ip:port与机器信息的字典
        if clone_type == CloneType.INSTANCE:
            address_machine_map = CloneHandler(
                bk_biz_id=bk_biz_id, operator=operator, clone_type=clone_type, clone_cluster_type=clone_cluster_type
            ).get_address__machine_map(clone_data_list)

        for clone_data in clone_data_list:
            # 实例化权限克隆记录，后续存到数据库中
            record = MySQLPermissionCloneRecord(
                ticket_id=ticket_id,
                bk_cloud_id=clone_data["bk_cloud_id"],
                source=clone_data["source"],
                target=clone_data["target"],
                clone_type=clone_type,
            )
            if clone_type == CloneType.CLIENT.value:
                record.target = "\n".join(record.target)

            # 权限克隆全局参数准备
            params = {
                "bk_biz_id": bk_biz_id,
                "operator": operator,
                "bk_cloud_id": clone_data["bk_cloud_id"],
                "cluster_type": clone_cluster_type,
            }
            try:
                # 调用客户端克隆/实例克隆
                if clone_type == CloneType.CLIENT.value:
                    params.update({"source_ip": clone_data["source"], "target_ip": clone_data["target"]})
                    if "user" in clone_data and "target_instances" in clone_data:
                        params.update({"user": clone_data["user"], "target_instances": clone_data["target_instances"]})
                    resp = DBPrivManagerApi.clone_client(params=params, raw=True)
                else:
                    params.update(
                        {
                            "source": {
                                "address": clone_data["source"],
                                "machine_type": address_machine_map[clone_data["source"]].machine_type,
                            },
                            "target": {
                                "address": clone_data["target"],
                                "machine_type": address_machine_map[clone_data["target"]].machine_type,
                            },
                        }
                    )
                    resp = DBPrivManagerApi.clone_instance(params=params, raw=True)

                # 填充克隆的结果和信息
                record.status = int(resp["code"]) == 0
                clone_success_count += record.status
                record.error = resp["message"]
                self.log_info(f"{resp['message']}\n")

            except Exception as e:  # pylint: disable=broad-except
                error_message = _("「权限克隆异常」{}").format(getattr(e, "message", e))
                record.status, record.error = False, error_message
                self.log_error(_("权限克隆失败，错误信息: {}\n").format(error_message))

            record.save()

        # 权限克隆结果汇总
        overall_result = clone_success_count == len(clone_data_list)
        self.log_info(
            _("权限克隆整体执行结果——总数:{}，成功数:{}，失败数:{}\n").format(
                len(clone_data_list), clone_success_count, len(clone_data_list) - clone_success_count
            )
        )
        self.log_info(
            _(
                "详情请下载excel: <a href='{}/apis/mysql/bizs/{}/permission/clone/"
                "get_clone_info_excel/?ticket_id={}&clone_type={}'>excel 下载</a>"
            ).format(env.BK_SAAS_HOST, bk_biz_id, ticket_id, clone_type)
        )
        return overall_result

    def inputs_format(self) -> List:
        return [Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True)]


class CloneRulesComponent(Component):
    name = __name__
    code = "clone_rules"
    bound_service = CloneRules
