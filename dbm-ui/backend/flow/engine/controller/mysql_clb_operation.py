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
from backend.flow.engine.bamboo.scene.name_service.mysql_clb_operation import MySQLClbFlow
from backend.flow.engine.controller.base import BaseController


class MySQLClbController(BaseController):
    """
    名字服务相关控制器
    """

    def clb_create(self):
        """
        创建clb
        """
        flow = MySQLClbFlow(root_id=self.root_id, data=self.ticket_data)
        flow.clb_create_flow()

    def clb_delete(self):
        """
        删除clb
        """
        flow = MySQLClbFlow(root_id=self.root_id, data=self.ticket_data)
        flow.clb_delete_flow()

    def immute_domain_bind_clb_ip(self):
        """
        主域名绑定clb ip
        """
        flow = MySQLClbFlow(root_id=self.root_id, data=self.ticket_data)
        flow.immute_domain_bind_clb_ip()

    def immute_domain_unbind_clb_ip(self):
        """
        主域名解绑clb ip
        """
        flow = MySQLClbFlow(root_id=self.root_id, data=self.ticket_data)
        flow.immute_domain_unbind_clb_ip()
