"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.flow.engine.bamboo.scene.sqlserver.validate.sqlserver_cluster_migrate_validator import (
    SqlserverClusterMigrateFlowValidator,
)
from backend.flow.engine.validate.exceptions import DuplicateIPException


class SqlserverClusterMigrateForInsFlowValidator(SqlserverClusterMigrateFlowValidator):
    """
    SqlserverClusterMigrateFlow类对应的validate类(集群拆分)
    判断传入flow的data参数合法性
    校验内容：
    每行入参校验：
        检验1：传入集群合法性
        检验2：判断传入集群ID列表，是否同级关联
    """

    def __call__(self):
        """
        发起校验, 实例函数化
        """
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info=info, index=index, is_check_is_all_in_group=False)
        if error_msgs:
            return error_msgs

        err = self.pre_check_duplicate_cluster_ids("cluster_ids")
        if err:
            raise DuplicateIPException(err)

        return None
