"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.flow.engine.validate.exceptions import DuplicateClusterException, DuplicateIPException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class MySQLProxySwitchValidator(MysqlBaseValidator):
    """
    替换proxy流程的validator方法
    判断传入flow的data参数合法性
    每行校验：
    检验1：每一行的传入集群的合法性
    校验2：每一行的传入机器ipv4的合法性
    校验3：每一行的传入集群和ip，是否是所属关系
    校验4：每一行的关联集群信息，是不是传全
    聚合校验：
    检验：同一个flow，传入机器不能重复
    校验：同一个flow，同一个集群，如果规格出现不一致，则不能提单
    """

    def run_check_for_info(self, info: dict, index: int, is_migrate_ins_task: bool = False) -> list:
        """
        @param info：  self.data["infos"]每个元素体
        @param index： 每个元素体的编号
        @param is_migrate_ins_task：是否是实例级别的迁移proxy单据触发校验，如果是标记True，默认False
        """
        row_key = info.get("row_key", "")

        # 检查每一行ip传入是否合法
        # 嵌套行的精准输出
        check_ip_errors = {"field": "origin_proxies", "errors": [], "index": index, "row_key": row_key}
        for index, check_host in enumerate(info["origin_proxies"]):
            log_format_tag = self.create_log_tag(field="origin_proxies", index=index, row_key=row_key)
            error_msg = self.pre_check_ip([check_host["ip"]], **log_format_tag)
            if error_msg:
                check_ip_errors["errors"].append(error_msg)
        if check_ip_errors["errors"]:
            return [check_ip_errors]

        # 检查每一行集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_ids", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist(info["cluster_ids"], **log_format_tag)
        if error_msg:
            return [error_msg]

        # 检查每一行传入的ip和集群信息，是否是所属关系
        # 嵌套行的精准输出
        check_ip_cluster_relation_errors = {
            "field": "origin_proxies",
            "errors": [],
            "index": index,
            "row_key": row_key,
        }
        for index, check_host in enumerate(info["origin_proxies"]):
            log_format_tag = self.create_log_tag(field="origin_proxies", index=index, row_key=row_key)
            error_msg = self.pre_check_mysql_proxy_in_cluster(
                [check_host["ip"]], info["cluster_ids"], **log_format_tag
            )
            if error_msg:
                check_ip_cluster_relation_errors["errors"].append(error_msg)
        if check_ip_cluster_relation_errors["errors"]:
            return [check_ip_cluster_relation_errors]

        if is_migrate_ins_task:
            return []

        # 检查每一行的ip的所属集群信息是否传全
        # 嵌套行的精准输出
        # 这里和实例级别拆分的流程是公用，但是这块实例级别拆分，不做这块检查
        check_proxy_clusters_included_errors = {
            "field": "origin_proxies",
            "errors": [],
            "index": index,
            "row_key": row_key,
        }
        for index, check_host in enumerate(info["origin_proxies"]):
            log_format_tag = self.create_log_tag(field="origin_proxies", index=index, row_key=row_key)
            error_msg = self.pre_check_proxy_clusters_included(
                proxy_ip=check_host["ip"],
                bk_cloud_id=int(check_host["bk_cloud_id"]),
                cluster_ids=info["cluster_ids"],
                **log_format_tag,
            )
            if error_msg:
                check_proxy_clusters_included_errors["errors"].append(error_msg)
        if check_proxy_clusters_included_errors["errors"]:
            return [check_proxy_clusters_included_errors]

        return []

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        print(self.data)
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，同一个集群，传入机器不能重复
        err = self.pre_check_duplicate_ip("origin_proxies")
        if err:
            raise DuplicateIPException(err)

        # 同一个flow，不能出现同一个集群
        err = self.pre_check_duplicate_cluster_ids("cluster_ids")
        if err:
            raise DuplicateClusterException(err)

        return None
