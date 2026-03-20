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
from dataclasses import asdict

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.flow.consts import DBM_SQLSERVER_JOB_LONG_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.sqlserver_sql_execute import SqlserverSQLExecuteFlow
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverDataExportFlow(SqlserverSQLExecuteFlow):
    """
    构建Sqlserver执行数据导出的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        """
        定义SQL脚本执行流程，执行多集群并发执行；多SQL文件顺序执行
        执行逻辑：
        1: 下发执行器
        2: 下发SQL文件
        3: 执行SQL文件
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        clusters = Cluster.objects.filter(id__in=self.data["cluster_ids"])

        if len(clusters) == 0 or len(clusters) != len(self.data["cluster_ids"]):
            raise Exception(f"cluster not found: cluster_ids[{self.data['cluster_ids']}]")

        # 合并下发需要变更的文件，不同的bk_cloud_id需要分组处理
        target_hosts = [
            Host(
                ip=c.storageinstance_set.get(
                    instance_inner_role=self.data["select_role"], is_stand_by=True
                ).machine.ip,
                bk_cloud_id=c.bk_cloud_id,
            )
            for c in clusters
        ]
        act_lists = [
            {
                "act_name": _("下发db-actuator介质"),
                "act_component_code": TransFileInWindowsComponent.code,
                "kwargs": asdict(
                    DownloadMediaKwargs(
                        target_hosts=target_hosts,
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    )
                ),
            },
            {
                "act_name": _("下发SQL文件"),
                "act_component_code": TransFileInWindowsComponent.code,
                "kwargs": asdict(
                    DownloadMediaKwargs(
                        target_hosts=target_hosts,
                        file_list=self.get_sql_files(),
                        file_target_path=self.sql_target_path,
                    )
                ),
            },
        ]

        main_pipeline.add_parallel_acts(acts_list=act_lists)

        for cluster in clusters:
            # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
            master_instance = cluster.storageinstance_set.get(instance_inner_role=self.data["select_role"])

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.default_flow_global_data)

            # 执行SQL文件,默认3小时超时
            sub_pipeline.add_act(
                act_name=_("集群{}在{}角色执行数据导出".format(cluster.immute_domain, self.data["select_role"])),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_data_export_payload.__name__,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                        component_kwargs={
                            "bk_biz_id": cluster.bk_biz_id,
                            "bk_cloud_id": cluster.bk_cloud_id,
                            "cluster_domain": cluster.immute_domain,
                            "instance_role": self.data["select_role"],
                            "exec_ports": [master_instance.port],
                            "sql_file_path": self.sql_target_path,
                            "execute_objects": self.data["execute_objects"],
                            "zip_file_name": self.data["dump_file_names"].get(str(cluster.id)),
                        },
                    )
                ),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}集群数据导出".format(cluster.immute_domain))))
        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        # main_pipeline.run_pipeline()
        main_pipeline.run_pipeline_with_sidecar(check_ai_monitor_cluster_list=self.data["cluster_ids"])
