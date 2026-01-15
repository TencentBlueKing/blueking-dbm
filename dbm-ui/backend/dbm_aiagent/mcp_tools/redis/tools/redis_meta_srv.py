"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging

from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models.cluster import Cluster

logger = logging.getLogger("root")


class RedisMetaService:
    """获取Redis元数据的服务"""

    def __init__(self, immute_domain: str):
        self.cluster_obj = Cluster.objects.get(immute_domain=immute_domain)

    def is_memory_redis(self):
        if self.cluster_obj.cluster_type in [
            ClusterType.TendisTendisSSDInstance.value,
            ClusterType.TendisPredixyTendisplusCluster.value,
        ]:
            return False
        else:
            return True

    def get_master_ip_list(self):
        pass

    def get_proxies():
        pass
