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
from backend.flow.engine.bamboo.scene.influxdb.influxdb_apply_flow import InfluxdbApplyFlow
from backend.flow.engine.bamboo.scene.influxdb.influxdb_destroy_flow import InfluxdbDestroyFlow
from backend.flow.engine.bamboo.scene.influxdb.influxdb_disable_flow import InfluxdbDisableFlow
from backend.flow.engine.bamboo.scene.influxdb.influxdb_enable_flow import InfluxdbEnableFlow
from backend.flow.engine.bamboo.scene.influxdb.influxdb_reboot_flow import InfluxdbRebootFlow
from backend.flow.engine.bamboo.scene.influxdb.influxdb_replace_flow import InfluxdbReplaceFlow
from backend.flow.engine.controller.base import BaseController


class InfluxdbController(BaseController):
    """
    Influxdb实例相关调用
    """

    def influxdb_apply_scene(self):
        """
        influxdb部署流程
        """
        flow = InfluxdbApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_influxdb_flow()

    def influxdb_enable_scene(self):
        """
        influxdb启用
        """
        flow = InfluxdbEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_influxdb_flow()

    def influxdb_disable_scene(self):
        """
        influxdb禁用
        """
        flow = InfluxdbDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_influxdb_flow()

    def influxdb_destroy_scene(self):
        """
        influxdb下架
        """
        flow = InfluxdbDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_influxdb_flow()

    def influxdb_reboot_scene(self):
        """
        influxdb重启
        """
        flow = InfluxdbRebootFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reboot_influxdb_flow()

    def influxdb_replace_scene(self):
        """
        influxdb替换流程
        """
        flow = InfluxdbReplaceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.replace_influxdb_flow()
