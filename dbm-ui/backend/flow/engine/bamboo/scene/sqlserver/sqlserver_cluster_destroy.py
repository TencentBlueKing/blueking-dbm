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
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DeleteClusterDnsKwargs
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import create_sqlserver_login_sid
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverDestroyFlow(BaseFlow):
    """
    构建Sqlserver执行集群下架的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        """
        定义下架的执行流程：
        1：关闭sqlserver进程
        2：清理域名
        3：清理元数据
        """

        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for cluster_id in self.data["cluster_ids"]:
            cluster = Cluster.objects.get(id=cluster_id)
            # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
            master_instance = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )

            # 获取集群的slave节点信息
            slave_infos = cluster.storageinstance_set.filter(instance_role=InstanceRole.BACKEND_SLAVE)
            slaves = [{"host": s.machine.ip, "port": s.port} for s in slave_infos]

            # 拼接所有实例list
            instances = [{"host": master_instance.machine.ip, "port": master_instance.port}] + slaves

            # 拼接子流程全局上下文
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("cluster_ids")
            sub_flow_context["cluster_id"] = cluster_id

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
                        target_hosts=[Host(ip=i["host"], bk_cloud_id=cluster.bk_cloud_id) for i in instances],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )

            # 并发卸载实例
            acts_list = []
            for instance in instances:
                acts_list.append(
                    {
                        "act_name": _("卸载实例[{}:{}]".format(instance["host"], instance["port"])),
                        "act_component_code": SqlserverActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                exec_ips=[Host(ip=instance["host"], bk_cloud_id=cluster.bk_cloud_id)],
                                get_payload_func=SqlserverActPayload.uninstall_sqlserver.__name__,
                                custom_params={"ports": [instance["port"]]},
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 清理集群域名
            sub_pipeline.add_act(
                act_name=_("回收集群域名"),
                act_component_code=MySQLDnsManageComponent.code,
                kwargs=asdict(
                    DeleteClusterDnsKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        delete_cluster_id=cluster.id,
                    )
                ),
            )

            # 清理元数据
            sub_pipeline.add_act(
                act_name=_("清理元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.cluster_destroy.__name__,
                    )
                ),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("{}集群下架".format(cluster.name))))

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
