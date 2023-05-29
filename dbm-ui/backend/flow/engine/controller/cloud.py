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

from backend.flow.engine.bamboo.scene.cloud.dbha_service_flow import CloudDBHAServiceFlow
from backend.flow.engine.bamboo.scene.cloud.dns_service_flow import CloudDNSServiceFlow
from backend.flow.engine.bamboo.scene.cloud.drs_service_flow import CloudDRSServiceFlow
from backend.flow.engine.bamboo.scene.cloud.nginx_service_flow import CloudNginxServiceFlow
from backend.flow.engine.bamboo.scene.cloud.redis_dts_server_service_flow import CloudRedisDtsServerServiceFlow
from backend.flow.engine.controller.base import BaseController

logger = logging.getLogger("Controller")


class CloudServiceController(BaseController):
    """
    云区域服务流程控制器
    """

    def nginx_apply_scene(self):
        """nginx 部署流程"""
        flow = CloudNginxServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_apply_flow()

    def nginx_reload_scene(self):
        """nginx 重启流程"""
        flow = CloudNginxServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reload_flow()

    def nginx_replace_scene(self):
        """nginx 替换流程"""
        flow = CloudNginxServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_replace_flow()

    def dns_apply_scene(self):
        """dns部署流程"""
        flow = CloudDNSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_apply_flow()

    def dns_add_scene(self):
        """dns新增流程"""
        flow = CloudDNSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_add_flow()

    def dns_reduce_scene(self):
        """dns裁撤流程"""
        flow = CloudDNSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reduce_flow()

    def dns_replace_scene(self):
        """dns替换流程"""
        flow = CloudDNSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_replace_flow()

    def dns_reload_scene(self):
        """dns重装流程"""
        flow = CloudDNSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reload_flow()

    def dbha_apply_scene(self):
        """dnha部署流程"""
        flow = CloudDBHAServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_apply_flow()

    def dbha_replace_scene(self):
        """dbha替换流程"""
        flow = CloudDBHAServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_replace_flow()

    def dbha_add_scene(self):
        """dbha新增流程"""
        flow = CloudDBHAServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_add_flow()

    def dbha_reduce_scene(self):
        """dbha裁撤流程"""
        flow = CloudDBHAServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reduce_flow()

    def dbha_reload_scene(self):
        """dbha重启流程"""
        flow = CloudDBHAServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reload_flow()

    def drs_apply_scene(self):
        """drs部署流程"""
        flow = CloudDRSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_apply_flow()

    def drs_reload_scene(self):
        """drs重试流程"""
        flow = CloudDRSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reload_flow()

    def drs_reduce_scene(self):
        """drs裁撤流程"""
        flow = CloudDRSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reduce_flow()

    def drs_add_scene(self):
        """drs新增流程"""
        flow = CloudDRSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_add_flow()

    def drs_replace_scene(self):
        """drs新增流程"""
        flow = CloudDRSServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_replace_flow()

    def redis_dts_server_apply_scene(self):
        """redis dts_server部署流程"""
        flow = CloudRedisDtsServerServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_apply_flow()

    def redis_dts_server_add_scene(self):
        """redis dts_server新增流程"""
        flow = CloudRedisDtsServerServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_add_flow()

    def redis_dts_server_reduce_scene(self):
        """redis dts_server裁撤流程"""
        flow = CloudRedisDtsServerServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reduce_flow()

    def redis_dts_server_replace_scene(self):
        """redis dts_server替换流程"""
        flow = CloudRedisDtsServerServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_replace_flow()

    def redis_dts_server_reload_scene(self):
        """redis dts_server重装流程"""
        flow = CloudRedisDtsServerServiceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.service_reload_flow()
