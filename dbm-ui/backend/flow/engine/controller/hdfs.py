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
from backend.flow.engine.bamboo.scene.hdfs.hdfs_apply_flow import HdfsApplyFlow
from backend.flow.engine.bamboo.scene.hdfs.hdfs_destroy_flow import HdfsDestroyFlow
from backend.flow.engine.bamboo.scene.hdfs.hdfs_disable_flow import HdfsDisableFlow
from backend.flow.engine.bamboo.scene.hdfs.hdfs_enable_flow import HdfsEnableFlow
from backend.flow.engine.bamboo.scene.hdfs.hdfs_reboot_flow import HdfsRebootFlow
from backend.flow.engine.bamboo.scene.hdfs.hdfs_replace_flow import HdfsReplaceFlow
from backend.flow.engine.bamboo.scene.hdfs.hdfs_scale_up_flow import HdfsScaleUpFlow
from backend.flow.engine.bamboo.scene.hdfs.hdfs_shrink_flow import HdfsShrinkFlow
from backend.flow.engine.controller.base import BaseController


class HdfsController(BaseController):
    """
    hdfs实例相关调用
    """

    def hdfs_apply_scene(self):
        """
        hdfs部署流程
        """
        flow = HdfsApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_hdfs_flow()

    def hdfs_expansion_scene(self):
        """
        hdfs扩容流程
        """
        flow = HdfsScaleUpFlow(root_id=self.root_id, data=self.ticket_data)
        flow.scale_up_hdfs_flow()

    def hdfs_enable_scene(self):
        """
        hdfs集群启用
        """
        flow = HdfsEnableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.enable_hdfs_flow()

    def hdfs_disable_scene(self):
        """
        hdfs集群禁用
        """
        flow = HdfsDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.disable_hdfs_flow()

    def hdfs_destroy_scene(self):
        """
        hdfs下架
        """
        flow = HdfsDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.destroy_hdfs_flow()

    def hdfs_shrink_scene(self):
        """
        hdfs缩容
        """
        flow = HdfsShrinkFlow(root_id=self.root_id, data=self.ticket_data)
        flow.shrink_hdfs_flow()

    def hdfs_replace_scene(self):
        """
        hdfs替换
        """
        flow = HdfsReplaceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.replace_hdfs_flow()

    def hdfs_reboot_scene(self):
        """
        hdfs重启
        """
        flow = HdfsRebootFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reboot_hdfs_flow()
