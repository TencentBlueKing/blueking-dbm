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
import copy
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import HdfsRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.hdfs.hdfs_sub_flow import HdfsOperationFlow
from backend.flow.utils.hdfs.hdfs_context_dataclass import ActKwargs, HdfsReplaceContext
from backend.flow.utils.hdfs.hdfs_flow_data_initializer import HdfsFlowDataInitializer
from backend.ticket.constants import TicketType


class HdfsReplaceFlow(HdfsOperationFlow):
    """
    构建hdfs集群申请流程的抽象类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
         @param data : 单据传递参数
        """
        super().__init__(root_id, data)
        self.data_with_role = HdfsFlowDataInitializer.init_replace_data(data)

    def replace_hdfs_flow(self):
        """
        替换 hdfs集群 节点
        """
        # Builder 传参 为封装好角色IP的数据结构
        hdfs_pipeline = Builder(root_id=self.root_id, data=self.data_with_role)
        trans_files = GetFileList(db_type=DBType.Hdfs)

        # 拼接活动节点需要的私有参数
        act_kwargs = ActKwargs(bk_cloud_id=self.data_with_role["bk_cloud_id"])
        act_kwargs.set_trans_data_dataclass = HdfsReplaceContext.__name__
        act_kwargs.file_list = trans_files.hdfs_apply(db_version=self.data_with_role["db_version"])

        # 需要将配置项写入
        act_kwargs.is_update_trans_data = True

        scale_up_data = self.__get_replace_dn_data(TicketType.HDFS_SCALE_UP)
        add_dn_sub_pipeline = self.build_add_dn_sub_flow(act_kwargs, scale_up_data)
        hdfs_pipeline.add_sub_pipeline(add_dn_sub_pipeline.build_sub_process(sub_name=_("集群DN替换-扩容DN")))

        shrink_data = self.__get_replace_dn_data(TicketType.HDFS_SHRINK)
        del_dn_sub_pipeline = self.build_del_dn_sub_flow(act_kwargs, shrink_data)
        hdfs_pipeline.add_sub_pipeline(del_dn_sub_pipeline.build_sub_process(sub_name=_("集群DN替换-缩容DN")))

        hdfs_pipeline.run_pipeline_with_sidecar(check_ai_monitor_cluster_list=[self.data["cluster_id"]])

    def __get_replace_dn_data(self, ticket_type: TicketType) -> dict:

        data = copy.deepcopy(self.data_with_role)
        data["ticket_type"] = ticket_type.value
        role = HdfsRoleEnum.DataNode.value
        # 子流程和 dbmeta 都从 nodes 取本次操作的 DN，和 Doris 替换复用扩缩容的方式一致
        if ticket_type == TicketType.HDFS_SCALE_UP:
            data["nodes"] = {role: self.data_with_role["new_nodes"][role]}
        elif ticket_type == TicketType.HDFS_SHRINK:
            data["nodes"] = {role: self.data_with_role["old_nodes"][role]}
        return data
