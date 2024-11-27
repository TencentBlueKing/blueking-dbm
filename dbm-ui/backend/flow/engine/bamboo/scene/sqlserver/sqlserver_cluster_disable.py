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
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import SqlserverLoginExecMode
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.drop_random_job_user import SqlserverDropJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.exec_sqlserver_login import ExecSqlserverLoginComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    DropRandomJobUserKwargs,
    ExecActuatorKwargs,
    ExecLoginKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import create_sqlserver_login_sid
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverDisableFlow(BaseFlow):
    """
    构建Sqlserver执行集群禁用的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        """
        定义禁用的执行流程
        """

        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for cluster_id in self.data["cluster_ids"]:
            cluster = Cluster.objects.get(id=cluster_id)
            master = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )

            # 拼接子流程全局上下文
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("cluster_ids")
            sub_flow_context["cluster_id"] = cluster_id
            sub_flow_context["port"] = master.port

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 创建随机账号
            sub_pipeline.add_act(
                act_name=_("create temp job account"),
                act_component_code=SqlserverAddJobUserComponent.code,
                kwargs=asdict(
                    CreateRandomJobUserKwargs(
                        cluster_ids=[cluster.id],
                        sid=create_sqlserver_login_sid(),
                    ),
                ),
            )

            # 下发执行器
            sub_pipeline.add_act(
                act_name=_("下发执行器"),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=[Host(ip=master.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )
            # 禁用预检测
            sub_pipeline.add_act(
                act_name=_("检查实例{}:{}是否有业务链接".format(master.machine.ip, master.port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_check_inst_process_payload.__name__,
                        custom_params={"is_force_kill": False},
                    )
                ),
            )

            # 并行禁用业务账号
            acts_list = []
            for instance in cluster.storageinstance_set.all():
                acts_list.append(
                    {
                        "act_name": _("[{}]禁用业务账号".format(instance.ip_port)),
                        "act_component_code": ExecSqlserverLoginComponent.code,
                        "kwargs": asdict(
                            ExecLoginKwargs(
                                cluster_id=cluster.id,
                                exec_mode=SqlserverLoginExecMode.DISABLE.value,
                                exec_ip=instance.machine.ip,
                            ),
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 主动kill掉业务进程
            sub_pipeline.add_act(
                act_name=_("主动在实例{}:{}kill业务链接".format(master.machine.ip, master.port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_check_inst_process_payload.__name__,
                        custom_params={"is_force_kill": True},
                    )
                ),
            )

            # 变更集群元数据
            sub_pipeline.add_act(
                act_name=_("录入db_meta元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.cluster_offline.__name__,
                    )
                ),
            )

            # 删除随机账号
            sub_pipeline.add_act(
                act_name=_("remove temp job account"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id])),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}集群禁用".format(cluster.name))))

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
