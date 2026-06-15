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

from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.spider.validate.exception import (
    SpiderCountFailedException,
    SpiderRoleFailedException,
)
from backend.flow.engine.bamboo.scene.spider.validate.spider_switch_nodes_validate import (
    TenDBClusterSwitchNodesFlowValidator,
)
from backend.flow.engine.validate.exceptions import DuplicateIPException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class TenDBClusterRebuildNodesFlowValidator(MysqlBaseValidator):
    """
    TenDBClusterRebuildNodesFlow类对应的validate类
    判断传入flow的data参数合法性
    校验内容：
    每行入参校验：
        检验1：传入集群合法性
        校验2：传入ip的合法性
        校验3：传入的spider角色的合法性
    聚合校验：
        检验1：同一个flow，同一个集群，传入机器不能有相同
        检验2：同一个flow，同一个集群，不能出现不同待重建的spider角色
        检验3：同一个flow，不能出现重复的cluster
        检验4：同一个flow，同一个集群同一个spider角色，待重建的节点数量不能大于等于集群中该角色的实例总数
    """

    def run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info
        @param index
        """
        row_key = info.get("row_key", "")
        error_msg_list = []

        # 检查ip传入是否合法
        log_format_tag = self.create_log_tag(field="spider_ip_list", index=index, row_key=row_key)
        error_msg = self.pre_check_ip([host["ip"] for host in info["spider_ip_list"]], **log_format_tag)
        if error_msg:
            error_msg_list.append(error_msg)

        # 检查集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_id", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist([info["cluster_id"]], **log_format_tag)
        if error_msg:
            error_msg_list.append(error_msg)

        # 检查待重建的spider角色是否合法
        log_format_tag = self.create_log_tag(field="rebuild_spider_role", index=index, row_key=row_key)
        error_msg = TenDBClusterSwitchNodesFlowValidator.pre_check_spider_role(
            info["rebuild_spider_role"], **log_format_tag
        )
        if error_msg:
            error_msg_list.append(error_msg)

        return error_msg_list

    def pre_check_rebuild_spider_count(self):
        """
        校验：同一个flow中，同一个集群、同一个spider角色，
        待重建的spider节点数量不能大于等于集群中该角色的实例总数
        （否则会导致集群该角色没有可用实例，影响业务连续性）
        """
        # 按 (cluster_id, rebuild_spider_role) 维度聚合待重建的ip数量
        rebuild_count_map = defaultdict(int)
        for info in self.data["infos"]:
            key = (int(info["cluster_id"]), info["rebuild_spider_role"])
            rebuild_count_map[key] += len(info["spider_ip_list"])

        err_msg = ""
        for (cluster_id, spider_role), rebuild_count in rebuild_count_map.items():
            cluster = Cluster.objects.get(id=cluster_id)
            exist_count = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=spider_role).count()
            if rebuild_count >= exist_count:
                err_msg += _("【{}】待重建的spider角色[{}]节点数量[{}]大于等于集群中该角色的实例总数[{}]，请检查\n").format(
                    cluster.immute_domain, spider_role, rebuild_count, exist_count
                )

        return err_msg

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

        # 阶段2 做聚合校验
        # 同一个flow，同一个集群，传入机器不能有相同
        err = self.pre_check_duplicate_ip("spider_ip_list")
        if err:
            raise DuplicateIPException(err)

        # 同一个flow，同一个集群，不能出现不同待重建的spider角色
        err = self.pre_check_spider_role_for_cluster("cluster_id", "rebuild_spider_role")
        if err:
            raise SpiderRoleFailedException(err)

        # 同一个flow，同一集群同一个spider角色，待重建节点数不能大于等于集群该角色实例总数
        err = self.pre_check_rebuild_spider_count()
        if err:
            raise SpiderCountFailedException(err)

        return None
