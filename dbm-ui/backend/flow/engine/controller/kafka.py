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

from backend.flow.engine.bamboo.scene.kafka.kafka_apply_flow import KafkaApplyFlow
from backend.flow.engine.bamboo.scene.kafka.kafka_destroy_flow import KafkaDestroyFlow
from backend.flow.engine.bamboo.scene.kafka.kafka_disable_flow import KafkaDisableFlow
from backend.flow.engine.bamboo.scene.kafka.kafka_enable_flow import KafkaEnableFlow
from backend.flow.engine.bamboo.scene.kafka.kafka_fake_apply_flow import KafkaFakeApplyFlow
from backend.flow.engine.bamboo.scene.kafka.kafka_reboot_flow import KafkaRebootFlow
from backend.flow.engine.bamboo.scene.kafka.kafka_replace_flow import KafkaReplaceFlow
from backend.flow.engine.bamboo.scene.kafka.kafka_scale_up_flow import KafkaScaleUpFlow
from backend.flow.engine.bamboo.scene.kafka.kafka_shrink_flow import KafkaShrinkFlow
from backend.flow.engine.controller.base import BaseController


class KafkaController(BaseController):
    """
    kafka实例相关调用
    """

    def kafka_apply_scene(self):
        """
        kafka部署流程
        """
        flow = KafkaApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_kafka_flow()

    def kafka_scale_up_scene(self):
        """
        kafka扩容流程
        """
        flow = KafkaScaleUpFlow(root_id=self.root_id, data=self.ticket_data)
        flow.scale_up_kafka_flow()

    def kafka_enable_scene(self):
        """
        kafka启用
        """
        flow = KafkaEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_kafka_flow()

    def kafka_disable_scene(self):
        """
        kafka禁用
        """
        flow = KafkaDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_kafka_flow()

    def kafka_destroy_scene(self):
        """
        kafka下架
        """
        flow = KafkaDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_kafka_flow()

    def kafka_shrink_scene(self):
        """
        kafka缩容
        """
        flow = KafkaShrinkFlow(root_id=self.root_id, data=self.ticket_data)
        flow.shrink_kafka_flow()

    def kafka_replace_scene(self):
        """
        kafka替换
        """
        flow = KafkaReplaceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.replace_kafka_flow()

    def kafka_reboot_scene(self):
        """
        kafka重启
        """
        flow = KafkaRebootFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reboot_kafka_flow()

    def kafka_fake_apply_scene(self):
        """
        kafka假部署流程
        """
        flow = KafkaFakeApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.fake_deploy_kafka_flow()
