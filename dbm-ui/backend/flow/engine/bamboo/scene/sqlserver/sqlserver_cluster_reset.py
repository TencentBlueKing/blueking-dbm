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
from backend.flow.consts import NoSync, SqlserverCleanMode, SqlserverLoginExecMode, SqlserverSyncModeMaps
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.drop_random_job_user import SqlserverDropJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.exec_sqlserver_login import ExecSqlserverLoginComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.mysql.mysql_act_dataclass import CreateDnsKwargs, DeleteClusterDnsKwargs
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    DropRandomJobUserKwargs,
    ExecActuatorKwargs,
    ExecLoginKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import create_sqlserver_login_sid, get_dbs_for_drs
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverResetFlow(BaseFlow):
    """
    构建Sqlserver执行集群重置的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        """
        定义集群重置的执行流程:
        1：清理业务账号
        2：清理业务数据库
        3：更改集群域名
        4：更新集群元信息、集群状态
        """

        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        slaves = []
        standby_slave = None

        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=info["cluster_id"])
            # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
            master_instance = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )

            # 获取集群的slave节点信息
            slave_infos = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_SLAVE)
            for s in slave_infos:
                if s.is_stand_by:
                    # 一个集群有且只有一个is_stand_by 为 true 的 slave
                    standby_slave = s
                slaves.append({"host": s.machine.ip, "port": s.port})

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
            sub_flow_context["clean_dbs"] = get_dbs_for_drs(cluster_id=cluster.id, db_list=["*"], ignore_db_list=[])
            sub_flow_context["clean_mode"] = SqlserverCleanMode.DROP_DBS.value
            sub_flow_context["clean_tables"] = ["*"]
            sub_flow_context["ignore_clean_tables"] = []

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

            # 下发执行器
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

            # 清理业务账号
            sub_pipeline.add_act(
                act_name=_("清理业务账号"),
                act_component_code=ExecSqlserverLoginComponent.code,
                kwargs=asdict(
                    ExecLoginKwargs(
                        cluster_id=cluster.id,
                        exec_mode=SqlserverLoginExecMode.DROP.value,
                    ),
                ),
            )

            # 清理业务数据库
            if len(sub_flow_context["clean_dbs"]) != 0:
                sub_pipeline.add_act(
                    act_name=_("清理数据库"),
                    act_component_code=SqlserverActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                            get_payload_func=SqlserverActPayload.get_clean_dbs_payload.__name__,
                        )
                    ),
                )

            # 清除集群旧的域名
            sub_pipeline.add_act(
                act_name=_("回收集群的旧域名"),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    DeleteClusterDnsKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        delete_cluster_id=cluster.id,
                    )
                ),
            )
            # 添加集群新的域名
            acts_list = [
                {
                    "act_name": _("添加集群域名"),
                    "act_component_code": MySQLDnsManageComponent.code,
                    "kwargs": asdict(
                        CreateDnsKwargs(
                            bk_cloud_id=cluster.bk_cloud_id,
                            add_domain_name=info["new_immutable_domain"],
                            dns_op_exec_port=sub_flow_context["port"],
                            exec_ip=master_instance.machine.ip,
                        )
                    ),
                }
            ]
            # 如果ha架构，则添加新从域名到is_stand_by=true的slave上
            if standby_slave:
                acts_list.append(
                    {
                        "act_name": _("添加从集群域名"),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            CreateDnsKwargs(
                                bk_cloud_id=cluster.bk_cloud_id,
                                add_domain_name=info["new_slave_domain"],
                                dns_op_exec_port=sub_flow_context["port"],
                                exec_ip=standby_slave.machine.ip,
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 变更集群元数据
            sub_pipeline.add_act(
                act_name=_("重置集群元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.cluster_reset.__name__,
                    )
                ),
            )

            # 删除随机账号
            sub_pipeline.add_act(
                act_name=_("drop job user"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id])),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}集群重置".format(cluster.name))))

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
