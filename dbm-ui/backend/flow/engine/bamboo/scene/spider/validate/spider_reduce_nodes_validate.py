"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import gettext as _

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import MIN_SPIDER_MASTER_COUNT_IN_TICKET, MIN_SPIDER_SLAVE_COUNT
from backend.flow.engine.bamboo.scene.spider.validate.exception import SpiderMinCountFailedException
from backend.flow.engine.bamboo.scene.spider.validate.spider_switch_nodes_validate import (
    TenDBClusterSwitchNodesFlowValidator,
)
from backend.flow.engine.validate.exceptions import DuplicateClusterException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class TenDBClusterReduceNodesFlowValidator(MysqlBaseValidator):
    """
    TenDBClusterReduceNodes类对应的validate类
    判断传入flow的data参数合法性
    校验内容：
    每行入参校验：
        检验1：传入集群合法性
        校验2：传入的spider角色的合法性
    聚合校验：
        检验1：同一个flow，统一集群，同一角色不能低于对应的下限
    """

    def pre_check_min_spider_count(self):
        """校验缩容后，spider节点能满足最小限度"""
        err_msg = ""

        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=int(info["cluster_id"]))

            spider_node_count = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=info["reduce_spider_role"]
            ).count()

            if info.get("spider_reduced_to_count") is None:
                # 代表手动输入机器缩容
                info["spider_reduced_to_count"] = spider_node_count - len(info["spider_reduced_hosts"])

            spider_reduced_to_count = info["spider_reduced_to_count"]
            if spider_reduced_to_count >= spider_node_count:

                err_msg += _("【{}】请保证缩容后的接入层数量小于当前节点数量").format(cluster.immute_domain)

            role = info["reduce_spider_role"]
            if (
                role == TenDBClusterSpiderRole.SPIDER_MASTER
                and spider_reduced_to_count < MIN_SPIDER_MASTER_COUNT_IN_TICKET
            ):

                err_msg += _("【{}】请保证缩容后的接入层spider master数量>={}").format(
                    cluster.immute_domain, MIN_SPIDER_MASTER_COUNT_IN_TICKET
                )

            if role == TenDBClusterSpiderRole.SPIDER_SLAVE and spider_reduced_to_count < MIN_SPIDER_SLAVE_COUNT:

                err_msg += _("【{}】请保证缩容后的接入层spider slave数量>={}").format(cluster.immute_domain, MIN_SPIDER_SLAVE_COUNT)

        return err_msg

    def run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info
        @param index
        """
        row_key = info.get("row_key", "")
        error_msg_list = []

        # 检查集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_id", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist([info["cluster_id"]], **log_format_tag)
        if error_msg:
            error_msg_list.append(error_msg)

        # 检查待缩容的spider角色是否合法
        log_format_tag = self.create_log_tag(field="reduce_spider_role", index=index, row_key=row_key)
        error_msg = TenDBClusterSwitchNodesFlowValidator.pre_check_spider_role(
            info["reduce_spider_role"], **log_format_tag
        )
        if error_msg:
            error_msg_list.append(error_msg)

        return error_msg_list

    def __call__(self):
        """
        发起校验, 实例函数化
        """

        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 同一个flow，不能出现重复集群
        err = self.pre_check_duplicate_cluster_ids("cluster_id")
        if err:
            raise DuplicateClusterException(err)

        # 同一个flow，不能出现重复集群
        err = self.pre_check_min_spider_count()
        if err:
            raise SpiderMinCountFailedException(err)

        return None
