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
from backend.flow.engine.bamboo.scene.spider.validate.exception import SpiderCountFailedException
from backend.flow.engine.bamboo.scene.spider.validate.spider_switch_nodes_validate import (
    TenDBClusterSwitchNodesFlowValidator,
)
from backend.flow.engine.validate.exceptions import DuplicateClusterException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class TenDBClusterAddNodesFlowValidator(MysqlBaseValidator):
    """
    TenDBClusterAddNodesFlow类对应的validate类
    判断传入flow的data参数合法性
    校验内容：
    每行入参校验：
        检验1：传入集群合法性
        校验2：传入的spider角色的合法性
    聚合校验：
        检验1：同一个flow，不能出現相同集群信息
        检查2：在同一集群内，不能会超过集群spider节点部署上限设定
    """

    def pre_check_spider_upper_limit(self):
        """
        校验是否超过集群的spider_master/mnt 出现数量上限
        """
        err_msg = ""

        # 一次性遍历收集所有角色
        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]
            if info["add_spider_role"] == TenDBClusterSpiderRole.SPIDER_SLAVE:
                # 如果是扩容spider slave，不做检查
                continue

            cluster = Cluster.objects.get(id=int(cluster_id))

            # 计算当前spider集群已经有了多少个spider_master/mnt节点
            cluster_spider_master_count = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role__in=[
                    TenDBClusterSpiderRole.SPIDER_MASTER,
                    TenDBClusterSpiderRole.SPIDER_MNT,
                ]
            ).count()

            # 判断扩容后是否超过集群上限的一半
            check_result, upper_limit_count = self.pre_check_spider_master_count(
                bk_biz_id=cluster.bk_biz_id,
                db_module_id=cluster.db_module_id,
                ready_to_add_count=int(info["add_spider_num"]),
                existing_count=cluster_spider_master_count,
                immute_domain=cluster.immute_domain,
                divisor=2,
            )
            if not check_result:
                # 代表集群在替换单据的过程中，产生的spider_master/mnt节点数，超过集群承载上限，则应该退出异常
                err_msg += _("【{}】请确保集群扩容接入层后主节点和运维节点的总和小于等于集群【{}】上限的一半").format(
                    cluster.immute_domain, upper_limit_count
                )

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

        # 检查待扩容的spider角色是否合法
        log_format_tag = self.create_log_tag(field="add_spider_role", index=index, row_key=row_key)
        error_msg = TenDBClusterSwitchNodesFlowValidator.pre_check_spider_role(
            info["add_spider_role"], **log_format_tag
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

        # 传入扩容节点过程中，在同一集群内，不能会超过集群spider节点部署上限的一半
        err = self.pre_check_spider_upper_limit()
        if err:
            raise SpiderCountFailedException(err)

        return None
