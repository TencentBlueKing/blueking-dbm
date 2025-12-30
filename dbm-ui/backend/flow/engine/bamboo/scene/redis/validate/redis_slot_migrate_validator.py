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

from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_redis_cluster_protocal
from backend.flow.engine.validate.exceptions import DuplicateIPException
from backend.flow.engine.validate.redis_base_validate import RedisBaseValidator


class SlotMigrateFlowValidator(RedisBaseValidator):
    """
    RedisSlotsMigrateFlow类 slot迁移对应的validate
    每行校验：
    1、架构是否符合rediscluster协议
    2、扩缩容后机器组数是否满足要求(至少需要3组、至少有3个分片）
    """

    def __run_check_for_info(self, info: dict) -> list:
        """
        @param info：
        @param index： 每个元素体的编号
        """
        cluster_id = info["cluster_id"]
        cluster = Cluster.objects.get(id=cluster_id)
        cluster_type = cluster.cluster_type
        cluster_domain = cluster.immute_domain
        # 检查目标分片数是否符合要求
        target_group_num = info["group_num"]
        if target_group_num < 3:
            raise Exception(_("集群{}目标机器数{}小于3，不符合预期".format(cluster_domain, target_group_num)))

        # 检查目标机器数是否符合要求
        target_shard_num = info["shard_num"]
        if target_shard_num < 3:
            raise Exception(_("集群{}目标分片数{}小于3，不符合预期".format(cluster_domain, target_shard_num)))

        # 检查集群架构是否rediscluster协议
        if not is_redis_cluster_protocal(cluster_type):
            raise Exception(_("集群{}类型{}不满足rediscluster协议，不允许发起slot迁移".format(cluster_domain, cluster_type)))

        return []

    def __call__(self):
        # 阶段1 检测每个行的数据合法性
        # 缺少rowkey,先直接抛异常
        for index, info in enumerate(self.data["infos"]):
            self.__run_check_for_info(info)

        # 同一个flow，不能出现同一个集群
        err = self.pre_check_duplicate_cluster_ids("cluster_id")
        if err:
            raise DuplicateIPException(err)

        return None
