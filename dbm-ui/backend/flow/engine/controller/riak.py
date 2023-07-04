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
from backend.flow.engine.bamboo.scene.riak.riak_cluster_apply_flow import RiakClusterApplyFlow
from backend.flow.engine.bamboo.scene.riak.riak_cluster_destroy_flow import RiakClusterDestroyFlow
from backend.flow.engine.bamboo.scene.riak.riak_cluster_scale_in_flow import RiakClusterScaleInFlow
from backend.flow.engine.bamboo.scene.riak.riak_cluster_scale_out_flow import RiakClusterScaleOutFlow
from backend.flow.engine.controller.base import BaseController


class RiakController(BaseController):
    """
    riak实例相关调用
    """

    def riak_cluster_apply_scene(self):
        """
        riak集群部署场景
        """
        flow = RiakClusterApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_riak_cluster_flow()

    def riak_cluster_scale_out_scene(self):
        """
        riak集群扩容场景
        """
        flow = RiakClusterScaleOutFlow(root_id=self.root_id, data=self.ticket_data)
        flow.riak_cluster_scale_out_flow()

    def riak_cluster_scale_in_scene(self):
        """
        riak集群缩容场景
        """
        flow = RiakClusterScaleInFlow(root_id=self.root_id, data=self.ticket_data)
        flow.riak_cluster_scale_in_flow()

    def riak_cluster_destroy_scene(self):
        """
        riak集群下架
        """
        flow = RiakClusterDestroyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.riak_cluster_destroy_flow()
