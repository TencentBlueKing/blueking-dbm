"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import List, Optional

from backend.flow.engine.bamboo.scene.sqlserver.validate.exception import DuplicateSRCClusterException
from backend.flow.engine.bamboo.scene.sqlserver.validate.sqlserver_db_construct_validator import (
    SqlserverDBConstructValidator,
)


class SqlserverDBRollbackInLocalValidator(SqlserverDBConstructValidator):
    """SQLServer 本地回档场景 validator。

    职责：
      - 复用 SqlserverDBConstructValidator 的全部行校验逻辑（源/目标集群存在性、
        rename_infos 与备份记录一致性、日志备份连续性等）
      - 仅在场景语义上不同：本地回档允许 src_cluster == dst_cluster，
        因此在触发 run_check_for_info 时固定 is_check_src_and_dst_cluster=False

    与父类差异：
      - 仅重写 __call__；其它方法（run_check_for_info / pre_check_dbs_in_backup_list /
        pre_check_log_backup_continuity）全部复用父类实现，避免逻辑漂移

    边界：
      - 目标集群 dst_cluster 在多条 info 中重复仍然报错（DuplicateSRCClusterException）
      - 单行校验失败 -> 直接返回错误列表，不进入聚合校验阶段
    """

    def __call__(self) -> Optional[List[str]]:
        """发起校验，实例函数化。

        与父类唯一差异：run_check_for_info 传 is_check_src_and_dst_cluster=False，
        因为本地回档场景下源集群与目标集群本就允许相同。

        :return: 错误消息列表；为空/None 表示校验通过
        边界：
          - 行级校验命中错误 -> 直接返回错误列表，不再执行聚合校验
          - 聚合校验发现 dst_cluster 重复 -> raise DuplicateSRCClusterException
        """
        # 阶段1：逐行校验，本地回档不强制 src != dst
        error_msgs: List[str] = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info=info, index=index, is_check_src_and_dst_cluster=False)
        if error_msgs:
            return error_msgs

        # 阶段2：聚合校验 —— 目标集群不允许在多条 info 中重复
        err = self.pre_check_duplicate_cluster_ids("dst_cluster")
        if err:
            raise DuplicateSRCClusterException(message=err)

        return None
