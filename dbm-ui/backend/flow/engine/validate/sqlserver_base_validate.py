"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import List

from backend.db_meta.models import Cluster
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class SqlserverBaseValidator(MysqlBaseValidator):
    """
    sqlserver的基础校验类
    """

    @staticmethod
    def pre_check_instance_inner_role(cluster_ids: List[int], check_inner_role: str):
        """
        根据传入的实例inner_role做校验, 检查集群是否有该类型的实例
        """
        error_msg = ""
        for cluster_id in cluster_ids:
            try:
                cluster = Cluster.objects.get(id=cluster_id)
                if cluster.storageinstance_set.filter(instance_inner_role=check_inner_role).exists():
                    continue

                error_msg += (
                    f"The cluster [{cluster.immute_domain}] does not contain "
                    f"an instance of this role [{check_inner_role}]\n"
                )

            except Cluster.DoesNotExist:
                error_msg += f"cluster_id[{cluster_id}] is not exist \n"

        return error_msg
