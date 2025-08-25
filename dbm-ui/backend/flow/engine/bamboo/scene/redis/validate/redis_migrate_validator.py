"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from collections import Counter

from django.utils.translation import ugettext as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.engine.validate.exceptions import DuplicateClusterException, DuplicateInsException
from backend.flow.engine.validate.redis_base_validate import RedisBaseValidator


class RedisSingleInsMigrateFlowValidator(RedisBaseValidator):
    """
    RedisSingleInsMigrateFlow类(主从实例迁移)对应的validate类
    每行校验：
    1、传入的主从端口是否冲突（如有需要，还需要对比目标机器端口）
    2、传入的主从版本是否一致（只能迁移至最高版本）
    3、传入的主从类型是否一致（cache/ssd）
    聚合校验：
    1、同一个flow，传入主从实例不允许重复
    """

    def __run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info：
        @param index： 每个元素体的编号
        """
        row_key = info.get("row_key", "")

        # 检查每一行传入的src_cluster中的所有实例是否合法
        cluster_id_list = []
        master_ins_list = []
        slave_ins_list = []
        for ins in info["src_cluster"]:
            cluster_id_list.append(ins["cluster_id"])
            master_ins_list.append(ins["master_ins"])
            slave_ins_list.append(ins["slave_ins"])
        log_format_tag = self.create_log_tag(field="src_cluster", index=index, row_key=row_key)
        error_msg = self.pre_check_instance(master_ins_list + slave_ins_list, **log_format_tag)
        if error_msg:
            return [error_msg]

        # 检查每一行的端口是否存在冲突
        port_ins_dict = {}
        for master_ins in master_ins_list:
            port = str.split(IP_PORT_DIVIDER)[1]
            if port in port_ins_dict:
                error_msg = _("{} 和 {} 端口冲突\n".format(master_ins, port_ins_dict[port]))
                return [error_msg]
            port_ins_dict[port] = master_ins

        cluster_type_set = set()
        cluster_version_set = set()
        for cluster_id in cluster_id_list:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
            cluster_type = cluster.cluster_type
            cluster_version = cluster.major_version

            cluster_type_set.add(cluster_type)
            cluster_version_set.add(cluster_version)

        # 检查每一行的实例类型是否一致
        if len(cluster_type_set) != 1:
            error_msg = _("src_cluster 存在多个类型 : {} \n".format(cluster_type_set))
            return [error_msg]

        # 检查每一行的实例版本是否允许变更
        error_msg = self.check_version_allow(list(cluster_version_set), info["db_version"])
        if error_msg:
            return [error_msg]

        return []

    def __check_duplicate_ins(self) -> list:
        """
        检查单据的实例是否存在重复
        """
        ins_list = []
        error_msg = ""
        for info in self.data["infos"]:
            for ins in info["src_cluster"]:
                ins_list.append(ins["master_ins"])
                ins_list.append(ins["slave_ins"])

        counts = Counter(ins_list)
        duplicates = [item for item, count in counts.items() if count > 1]
        for d in duplicates:
            error_msg += _("{} 实例重复\n".format(d))
        if error_msg:
            return [error_msg]
        return []

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.__run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，同一个集群，传入机器不能重复
        err = self.__check_duplicate_ins()
        if err:
            raise DuplicateInsException(err)

        return None


class RedisClusterInsMigrateFlowValidator(RedisBaseValidator):
    """
    RedisClusterInsMigrateFlow类(集群实例迁移)对应的validate类
    每行校验：
        - 传入的实例是否属于同一集群
        - 传入的实例是否重复
    整体校验：
        - 单集群单info
    """

    def __run_check_for_info(self, info: dict, index: int) -> list:
        """
        @param info：
        @param index： 每个元素体的编号
        """
        row_key = info.get("row_key", "")
        log_format_tag = self.create_log_tag(field="src_cluster", index=index, row_key=row_key)

        ins_list = []
        error_msg = ""
        for migrate_info in info["migrate_list"]:
            ins = migrate_info["src_ins"]
            ins_list.append(ins)

        # 检查传入的实例是否重复
        counts = Counter(ins_list)
        duplicates = [item for item, count in counts.items() if count > 1]
        for d in duplicates:
            error_msg += _("{} 实例重复\n".format(d))
        if error_msg:
            return [error_msg]

        # 检查传入的所有实例是否合法
        error_msg = self.pre_check_instance(ins_list, **log_format_tag)
        if error_msg:
            return [error_msg]

        # 检查实例与cluster_id对应或者多个主从
        cluster_id = info["cluster_id"]
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])

        for ins in ins_list:
            ip, port = ins.split(IP_PORT_DIVIDER)

            cluster_ins_count = cluster.storageinstance_set.filter(machine__ip=ip, port=port).count()
            if cluster_ins_count != 1:
                error_msg += _(
                    "{} 实例在集群 {}-{} 个数为 {}\n".format(ins, cluster.immute_domain, cluster_id, cluster_ins_count)
                )
        if error_msg:
            return [error_msg]

        return []

    def __check_duplicate_cluster(self) -> list:
        """
        检查单据的实例是否存在重复
        """
        cluster_list = []
        error_msg = ""
        for info in self.data["infos"]:
            cluster_list.append(info["cluster_id"])

        counts = Counter(cluster_list)
        duplicates = [item for item, count in counts.items() if count > 1]
        for d in duplicates:
            error_msg += _("{} 集群重复\n".format(d))
        if error_msg:
            return [error_msg]
        return []

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.__run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 做聚合校验
        # 同一个flow，不能存在多个集群的单
        err = self.__check_duplicate_cluster()
        if err:
            raise DuplicateClusterException(err)

        return None
