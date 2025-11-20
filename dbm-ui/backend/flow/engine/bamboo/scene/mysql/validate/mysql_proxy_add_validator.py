"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.db_meta.enums import AccessLayer
from backend.flow.engine.validate.exceptions import DuplicateClusterIDException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class MySQLProxyClusterAddFlowValidator(MysqlBaseValidator):
    """
    MySQLProxyClusterAddFlow类对应的validate类
    判断传入flow的data参数合法性
    每行校验：
    检验1：传入集群的基础信息合法性
    检验2: 每一行的cluster_ids属性，是同关联集群信息，必须都关联出来，如果有漏，或者不满足“同组关联”，则校验不通过。
    聚合校验：
    检验3：同一个flow，不能出现重复集群ID
    """

    def run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info：  self.data["infos"]每个元素体
        @param index： 每个元素体的编号
        """
        row_key = info.get("row_key", "")

        # 检查每一行集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_ids", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist(info["cluster_ids"], **log_format_tag)
        if error_msg:
            return [error_msg]

        error_msg = self.pre_check_same_group_relationship(info["cluster_ids"], AccessLayer.PROXY, True)
        if error_msg:
            return [{"field": "cluster_ids", "index": index, "row_key": row_key, "errors": error_msg}]

        return []

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，同一个集群，传入cluster_id不能重复
        err = self.pre_check_duplicate_cluster_ids("cluster_ids")
        if err:
            raise DuplicateClusterIDException(err)

        return None
