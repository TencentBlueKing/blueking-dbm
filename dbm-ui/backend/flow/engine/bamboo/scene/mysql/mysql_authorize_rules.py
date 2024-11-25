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

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import authorize_sub_flow, clone_rules_sub_flow

logger = logging.getLogger("flow")


class MySQLAuthorizeRulesFlows(object):
    """
    授权mysql权限的流程抽象类
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
        mysql_authorize_rules.add_sub_pipeline(
            sub_flow=authorize_sub_flow(
                root_id=self.root_id,
                uid=self.data["uid"],
                bk_biz_id=self.data["bk_biz_id"],
                operator=self.data["created_by"],
                rules_set=self.data["rules_set"],
            )
        )
        mysql_authorize_rules.run_pipeline()

    def clone_mysql_rules(self):
        """定义mysql权限克隆流程"""

        mysql_clone_rules = Builder(root_id=self.root_id, data=self.data)
        mysql_clone_rules.add_sub_pipeline(
            sub_flow=clone_rules_sub_flow(
                root_id=self.root_id,
                bk_biz_id=self.data["bk_biz_id"],
                uid=self.data["uid"],
                clone_type=self.data["clone_type"],
                clone_data_list=self.data["clone_data"],
                clone_cluster_type=self.data["clone_cluster_type"],
                operator=self.data["created_by"],
            )
        )
        mysql_clone_rules.run_pipeline()
