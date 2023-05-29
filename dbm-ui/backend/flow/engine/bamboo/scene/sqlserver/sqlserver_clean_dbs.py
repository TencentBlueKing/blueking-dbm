"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import copy
import logging.config
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import NoSync, SqlserverSyncModeMaps
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.drop_random_job_user import SqlserverDropJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DownloadMediaKwargs,
    DropRandomJobUserKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import create_sqlserver_login_sid
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverCleanDBSFlow(BaseFlow):
    """
    构建Sqlserver执行数据库清档的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        """
        定义数据库重名命名的执行流程，支持多集群并发执行
        执行逻辑：
        1: 下发执行器
        2: 执行清档
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 获取集群的master节点,默认统一在master节点发起重命名
            cluster = Cluster.objects.get(id=info["cluster_id"])
            # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
            master_instance = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )
            # 获取集群的slave节点信息
            slave_infos = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_SLAVE)
            slaves = [{"host": s.machine.ip, "port": s.port} for s in slave_infos]

            # 获取集群数据库同步模式
            if cluster.cluster_type == ClusterType.SqlserverSingle:
                sync_mode = NoSync
            else:
                sync_mode = SqlserverSyncModeMaps[
                    SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
                ]

            # 拼接子流程全局上下文
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context["port"] = master_instance.port
            sub_flow_context["slaves"] = slaves
            sub_flow_context["sync_mode"] = sync_mode

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 创建随机账号
            sub_pipeline.add_act(
                act_name=_("create job user"),
                act_component_code=SqlserverAddJobUserComponent.code,
                kwargs=asdict(
                    CreateRandomJobUserKwargs(
                        cluster_ids=[cluster.id],
                        sid=create_sqlserver_login_sid(),
                    ),
                ),
            )

            sub_pipeline.add_act(
                act_name=_("下发执行器"),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )

            # 执行数据库清档
            sub_pipeline.add_act(
                act_name=_("执行数据库清档"),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_clean_dbs_payload.__name__,
                    )
                ),
            )

            # 删除随机账号
            sub_pipeline.add_act(
                act_name=_("drop job user"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id])),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}集群执行清档".format(cluster.name))))

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
