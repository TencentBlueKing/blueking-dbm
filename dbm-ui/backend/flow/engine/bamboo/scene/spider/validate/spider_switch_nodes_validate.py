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

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.spider.validate.exception import SpiderRoleFailedException
from backend.flow.engine.validate.base_validate import validator_log_format
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class TenDBClusterSwitchNodesFlowValidator(MysqlBaseValidator):
    """
    TenDBClusterSwitchNodesFlow类对应的validate类
    判断传入flow的data参数合法性
    检验1：传入集群、ip、spider角色的基础信息合法性
    检验2：传入替换节点过程中，是否会超过集群上限
    检验3：同一个flow，同一个集群，传入机器不能有相同
    检验4：同一个flow，同一个集群，不能出现不同待替换的spider角色
    检验5：同一个flow，同一个集群，不能出现不同的替换规格
    """

    @classmethod
    @validator_log_format
    def pre_check_spider_role(cls, spider_role):
        """
        校验传入进来的spider_role是否非法
        """
        if spider_role not in [TenDBClusterSpiderRole.SPIDER_MASTER, TenDBClusterSpiderRole.SPIDER_SLAVE]:
            return f"{spider_role} is not support \n"

        return ""

    def pre_check_spider_upper_limit(self):
        """
        校验是否超过集群的spider_master/mnt 出现数量上限
        """
        switch_count_for_cluster_set = defaultdict(int)

        # 一次性遍历收集所有角色
        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]
            if info["switch_spider_role"] == TenDBClusterSpiderRole.SPIDER_MASTER:
                switch_count_for_cluster_set[cluster_id] += 1

        # 找出大于1的set
        err_msg = ""
        for cluster_id, count in switch_count_for_cluster_set.items():
            try:
                cluster = Cluster.objects.get(id=int(cluster_id))
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(cluster_id=int(cluster_id), message=_("集群不存在"))

            # 计算当前spider集群已经有了多少个spider_master/mnt节点
            cluster_spider_master_count = cluster.proxyinstance_set.filter(
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
            ).count()

            check_result, upper_limit_count = self.pre_check_spider_master_count(
                bk_biz_id=cluster.bk_biz_id,
                db_module_id=cluster.db_module_id,
                ready_to_add_count=count,
                existing_count=cluster_spider_master_count,
                immute_domain=cluster.immute_domain,
            )
            if not check_result:
                # 代表集群在替换单据的过程中，产生的spider_master/mnt节点数，超过集群承载上限，则应该退出异常
                err_msg += _(
                    "[{}]预估替换节点中会超过集群上限，请减少本次单据的替换数量, 集群上限数:{};替换数:{};集群存在数:{} \n".format(
                        cluster.immute_domain, upper_limit_count, count, cluster_spider_master_count
                    )
                )

        return err_msg

    def __run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info
        @param index
        """
        row_key = info.get("row_key", "")
        error_msg_list = []

        # 检查ip传入是否合法
        log_format_tag = self.create_log_tag(field="spider_old_ip_list", index=index, row_key=row_key)
        error_msg = self.pre_check_ip([host["ip"] for host in info["spider_old_ip_list"]], **log_format_tag)
        if error_msg:
            error_msg_list.append(error_msg)

        # 检查集群是否存在
        log_format_tag = self.create_log_tag(field="cluster_id", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist([info["cluster_id"]], **log_format_tag)
        if error_msg:
            error_msg_list.append(error_msg)

        # 检查spider
        log_format_tag = self.create_log_tag(field="switch_spider_role", index=index, row_key=row_key)
        error_msg = self.pre_check_spider_role(info["switch_spider_role"], **log_format_tag)
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
            error_msgs += self.__run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，不能出现同样的ip
        err = self.pre_check_duplicate_ip("spider_old_ip_list")
        if err:
            raise SpiderRoleFailedException(err)

        # 同一个flow，同一个集群，不能出现不同待替换的spider角色
        err = self.pre_check_spider_role_for_cluster("cluster_id", "switch_spider_role")
        if err:
            raise SpiderRoleFailedException(err)

        # 同一个flow，同一个集群，不能出现不同的替换规格
        err = self.pre_check_spider_spec_for_cluster("cluster_id")
        if err:
            raise SpiderRoleFailedException(err)

        # 传入替换节点是否超过集群上限的一半
        err = self.pre_check_spider_upper_limit()
        if err:
            raise SpiderRoleFailedException(err)

        return None
