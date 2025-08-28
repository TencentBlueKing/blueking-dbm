"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from collections import defaultdict

from django.utils.translation import ugettext as _

from backend.flow.engine.validate.exceptions import DuplicateIPException
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

    def pre_check_spec_group_by_cluster(self) -> str:
        """
        将单据参数，按照集群ID分类，如果单据中，同一个集群，替换两个以上的proxy，且存在不同规格，则校验不通过
        """
        err_msg = ""
        cluster_id_spec = defaultdict(set)
        for info in self.data["infos"]:
            for cluster_id in info["cluster_ids"]:
                cluster_id_spec[cluster_id].add(info["origin_proxy_ip"]["spec"]["id"])

        for cluster_id, spec_set in cluster_id_spec.items():
            if len(spec_set):
                err_msg += _("在单据中，集群ID [{}] 出现两个以上的不同proxy规格的替换，请检查 \n".format(cluster_id))

        return err_msg

    def run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info：  self.data["infos"]每个元素体
        @param index： 每个元素体的编号
        """
        row_key = info.get("row_key", "")

        # 检查每一行ip传入是否合法
        log_format_tag = self.create_log_tag(field="origin_proxy_ip", index=index, row_key=row_key)
        error_msg = self.pre_check_ip([info["origin_proxy_ip"]["ip"]], **log_format_tag)
        if error_msg:
            return [error_msg]

        # 检查每一行集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_ids", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist(info["cluster_ids"], **log_format_tag)
        if error_msg:
            return [error_msg]

        # 检查每一行传入的ip和集群信息，是否是所属关系
        log_format_tag = self.create_log_tag(field="origin_proxy_ip", index=index, row_key=row_key)
        error_msg = self.pre_check_mysql_proxy_in_cluster(
            [info["origin_proxy_ip"]["ip"]], info["cluster_ids"], **log_format_tag
        )
        if error_msg:
            return [error_msg]

        # 检查每一行的ip的所属集群信息是否传全
        log_format_tag = self.create_log_tag(field="origin_proxy_ip", index=index, row_key=row_key)
        error_msg = self.pre_check_proxy_clusters_included(
            proxy_ip=info["origin_proxy_ip"]["ip"],
            bk_cloud_id=int(info["origin_proxy_ip"]["bk_cloud_id"]),
            cluster_ids=info["cluster_ids"],
            **log_format_tag,
        )
        if error_msg:
            return [error_msg]

        return []

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，同一个集群，传入机器不能重复
        err = self.pre_check_duplicate_ip("origin_proxy_ip")
        if err:
            raise DuplicateIPException(err)

        # 同一个flow，同一个集群，不能出现2个以上的proxy规格
        # todo 后续添加

        return None
