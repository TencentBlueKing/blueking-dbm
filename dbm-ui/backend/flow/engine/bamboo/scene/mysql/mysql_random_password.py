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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBPrivManagerApi
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.external_service import ExternalServiceComponent
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


def random_password_callback(params, data, kwargs, global_data):
    """密码随机化成功后的回调函数, 记录随机化成功和失败IP"""
    flow = Ticket.objects.get(id=global_data["uid"]).current_flow()
    ticket_data = flow.details["ticket_data"]
    ticket_data.update(random_results=data)
    flow.save(update_fields=["details"])


class MySQLRandomizePassword(object):
    """
    mysql密码随机化
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def mysql_randomize_password(self):
        """定义mysql密码随机化流程"""
        mysql_authorize_rules = Builder(root_id=self.root_id, data=self.data)
        mysql_authorize_rules.add_act(
            act_name=_("mysql密码随机化"),
            act_component_code=ExternalServiceComponent.code,
            kwargs={
                "params": self.data,
                "api_import_path": DBPrivManagerApi.__module__,
                "api_import_module": "DBPrivManagerApi",
                "api_call_func": "modify_admin_password",
                "success_callback_path": f"{random_password_callback.__module__}.{random_password_callback.__name__}",
            },
        )
        mysql_authorize_rules.run_pipeline()
