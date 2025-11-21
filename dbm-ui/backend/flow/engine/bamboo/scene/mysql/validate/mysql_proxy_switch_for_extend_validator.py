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
from backend.flow.engine.validate.exceptions import DuplicateIPException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class MySQLProxySwitchForExtendValidator(MysqlBaseValidator):
    """
    proxy升降配流程的validator方法
    判断传入flow的data参数合法性
    每行校验：
    检验1：每一行的传入集群的合法性
    校验2：每一行的传入集群和ip，是否是所属关系
    校验3：每一行的cluster_ids属性，是同关联集群信息，必须都关联出来，如果有漏，或者不满足“同组关联”，则校验不通过。
    校验4：每一行的中待替换机器origin_proxy_ips列表信息， 是否传入所有集群的全部
    聚合校验：
    检验1：同一个flow，不能传入重复的集群

    """

    def run_check_for_info(self, info: dict, index: int, is_check_is_all_in_group: bool) -> list:
        """
        @param info: self.data["infos"]每个元素体
        @param index: 每个元素体的行编号
        @param is_check_is_all_in_group: 控制是否检测做全部传入的同组共享检测的开关
        """
        row_key = info.get("row_key", "")

        # 检查每一行集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_ids", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist(info["cluster_ids"], **log_format_tag)
        if error_msg:
            return [error_msg]

        # 检查每一行传入的ip和集群信息，是否是所属关系
        log_format_tag = self.create_log_tag(field="cluster_ids", index=index, row_key=row_key)
        error_msg = self.pre_check_mysql_proxy_in_cluster(
            [i["ip"] for i in info["origin_proxies"]], info["cluster_ids"], **log_format_tag
        )
        if error_msg:
            return [error_msg]

        # 检查每一行中集群列表的所属关系，是否属于同组共享，判断机器类型维度是proxy, 并且检测中同组共享的集群信息，是否全部传入
        error_msg = self.pre_check_same_group_relationship(
            info["cluster_ids"], AccessLayer.PROXY, is_check_is_all_in_group
        )
        if error_msg:
            return [{"field": "cluster_ids", "index": index, "row_key": row_key, "errors": error_msg}]

        # 检查每一行中待替换机器origin_proxies列表信息， 是否传入所有集群的全部
        machines_set = set([i["ip"] for i in info["origin_proxies"]])
        error_msgs = ""
        for cluster_id in info["cluster_ids"]:
            error_msg = self.per_check_all_machine_in_cluster(cluster_id, machines_set, AccessLayer.PROXY)
            if error_msg:
                error_msgs += f"{error_msg}\n"
        if error_msgs:
            return [{"field": "cluster_ids", "index": index, "row_key": row_key, "errors": error_msgs}]

        return []

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info=info, index=index, is_check_is_all_in_group=True)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，不能出现同一个集群
        err = self.pre_check_duplicate_cluster_ids("cluster_ids")
        if err:
            raise DuplicateIPException(err)

        return None
