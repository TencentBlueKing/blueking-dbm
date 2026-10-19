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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.hdfs.hdfs_sub_flow import HdfsOperationFlow
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, HdfsApplyContext
from backend.flow.utils.hdfs.hdfs_flow_data_initializer import HdfsFlowDataInitializer


class HdfsScaleUpFlow(HdfsOperationFlow):
    """
    构建hdfs扩容流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
         @param data : 单据传递参数
        """
        super().__init__(root_id, data)
        self.data_with_role = HdfsFlowDataInitializer.init_scale_up_data(data)

    def scale_up_hdfs_flow(self):
        """
        扩容hdfs集群流程
        """
        hdfs_pipeline = Builder(root_id=self.root_id, data=self.data_with_role)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        act_kwargs = ActKwargs(bk_cloud_id=self.data_with_role["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsApplyContext.__name__
        act_kwargs.file_list = trans_files.hdfs_apply(db_version=self.data_with_role["db_version"])
        act_kwargs.is_update_trans_data = True

        add_dn_sub_pipeline = self.build_add_dn_sub_flow(act_kwargs, self.data_with_role)
        hdfs_pipeline.add_sub_pipeline(add_dn_sub_pipeline.build_sub_process(sub_name=_("集群DN扩容")))
        hdfs_pipeline.run_pipeline_with_sidecar(check_ai_monitor_cluster_list=[self.data["cluster_id"]])
