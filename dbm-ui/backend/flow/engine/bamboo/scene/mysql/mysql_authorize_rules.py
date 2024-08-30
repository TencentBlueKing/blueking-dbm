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

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.mysql.authorize_rules import AuthorizeRulesComponent
from backend.flow.plugins.components.collections.mysql.clone_rules import CloneRulesComponent

logger = logging.getLogger("flow")


class MySQLAuthorizeRulesFlows(object):
    """
    授权mysql权限的流程抽象类
    todo 后续需要兼容跨云管理 bk_cloud_id
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """

        self.root_id = root_id
        self.data = data

    def authorize_mysql_rules(self):
        """定义mysql授权流程"""

        mysql_authorize_rules = Builder(root_id=self.root_id, data=self.data)
        mysql_authorize_rules.add_act(
            act_name=_("添加mysql规则授权"), act_component_code=AuthorizeRulesComponent.code, kwargs=self.data
        )
        mysql_authorize_rules.run_pipeline()

    def clone_mysql_rules(self):
        """定义mysql授权流程"""

        mysql_clone_rules = Builder(root_id=self.root_id, data=self.data)
        mysql_clone_rules.add_act(
            act_name=_("添加mysql权限克隆"), act_component_code=CloneRulesComponent.code, kwargs=self.data
        )
        mysql_clone_rules.run_pipeline()
