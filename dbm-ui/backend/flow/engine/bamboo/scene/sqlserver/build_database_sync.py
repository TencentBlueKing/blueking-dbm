"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging.config

from django.utils.translation import ugettext as _

from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import sync_dbs_for_cluster_sub_flow
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverBuildDBSyncFlow(BaseFlow):
    """
    构建Sqlserver的数据库建立同步的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        """
        定义Sqlserver的数据库建立同步的执行流程，支持多集群并发执行
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 获取集群的master节点,默认统一在master节点备份
            cluster = Cluster.objects.get(id=info["cluster_id"])
            slave_instance = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_SLAVE)

            sync_slaves = []
            for slave in slave_instance:
                if slave.status != InstanceStatus.RUNNING:
                    # 如果其中一个slave出现异常，则不做db同步
                    raise Exception(f"the slave [{slave.ip_port}] status is {slave.status}, not running ,check")
                sync_slaves.append(Host(ip=slave.machine.ip, bk_cloud_id=cluster.bk_cloud_id))

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_sub_pipeline(
                sub_flow=sync_dbs_for_cluster_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster,
                    sync_slaves=sync_slaves,
                    sync_dbs=info["sync_dbs"],
                )
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}集群建立数据库同步".format(cluster.name))))

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
