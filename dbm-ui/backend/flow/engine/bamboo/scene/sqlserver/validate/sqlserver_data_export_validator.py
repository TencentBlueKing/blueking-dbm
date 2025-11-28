"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.validate.exceptions import DuplicateClusterException
from backend.flow.engine.validate.sqlserver_base_validate import SqlserverBaseValidator


class SqlserverDataExportValidator(SqlserverBaseValidator):
    """
    SqlserverDataExportFlow类对应的validate类
    判断传入flow的data参数合法性
    """

    def __call__(self):
        """
        发起校验, 实例函数化
        """
        # 检查传入的集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_ids", index=0, row_key="")
        error_msg = self.pre_check_cluster_exist(self.data["cluster_ids"], **log_format_tag)
        if error_msg:
            raise DuplicateClusterException(error_msg)

        # 检查传入的集群是否有对应的实例角色
        error_msg = self.pre_check_instance_inner_role(self.data["cluster_ids"], self.data["select_role"])
        if error_msg:
            raise DuplicateClusterException(error_msg)

        return None
