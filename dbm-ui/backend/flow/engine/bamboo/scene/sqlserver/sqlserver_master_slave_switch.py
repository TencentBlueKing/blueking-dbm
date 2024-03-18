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
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import SqlserverSyncModeMaps
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import (
    clone_configs_sub_flow,
    pre_check_sub_flow,
    switch_domain_sub_flow_for_cluster,
)
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.drop_random_job_user import SqlserverDropJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    DropRandomJobUserKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import create_sqlserver_login_sid
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverSwitchFlow(BaseFlow):
    """
    构建Sqlserver执行数据库互切的流程类
    兼容跨云集群的执行
    """

    def run_flow(self):
        """
        定义集群互切的执行流程，支持多集群并发执行
        执行逻辑：
        1：给slave(is_stand_by=true) 下发执行器
        2：预检测（安全模式）
        3：克隆配置（安全模式）
        4：执行互切
        5：切换域名
        6：变更元数据
        """

        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 声明子流程
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_context)

            sub_pipeline.add_act(
                act_name=_("下发执行器"),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=[Host(**info["slave"])],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )
            act_list = []
            for cluster_id in info["cluster_ids"]:
                # 以集群维度操作切换子流程
                cluster = Cluster.objects.get(id=cluster_id)
                old_master = cluster.storageinstance_set.get(machine__ip=info["master"]["ip"])
                new_master = cluster.storageinstance_set.get(machine__ip=info["slave"]["ip"])

                # 判断传入slave的is_stand_by是否为true
                if not new_master.is_stand_by:
                    raise Exception(
                        f"The [{info['slave']}]'s is_stand_by is false and cannot be used as the new master"
                    )

                # 获取集群数据库同步模式
                sync_mode = SqlserverSyncModeMaps[
                    SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
                ]

                # 拼接子流程全局上下文
                cluster_context = copy.deepcopy(self.data)
                cluster_context.pop("infos")
                cluster_context["master_host"] = old_master.machine.ip
                cluster_context["master_port"] = old_master.port
                cluster_context["port"] = new_master.port
                cluster_context["sync_mode"] = sync_mode

                # 启动子流程
                cluster_pipeline = SubBuilder(root_id=self.root_id, data=cluster_context)

                # 创建随机账号
                cluster_pipeline.add_act(
                    act_name=_("create job user"),
                    act_component_code=SqlserverAddJobUserComponent.code,
                    kwargs=asdict(
                        CreateRandomJobUserKwargs(
                            cluster_ids=[cluster.id],
                            sid=create_sqlserver_login_sid(),
                        ),
                    ),
                )

                if not self.data["force"]:
                    # 如果是强制模式，不做预检测, 不做克隆
                    cluster_pipeline.add_sub_pipeline(
                        sub_flow=pre_check_sub_flow(
                            uid=self.data["uid"],
                            root_id=self.root_id,
                            check_host=Host(ip=old_master.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                            check_port=old_master.port,
                        )
                    )

                    # 先做克隆周边配置，保证这块内容切换前是同步的
                    cluster_pipeline.add_sub_pipeline(
                        sub_flow=clone_configs_sub_flow(
                            uid=self.data["uid"],
                            root_id=self.root_id,
                            source_host=Host(ip=old_master.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                            source_port=old_master.port,
                            target_host=Host(ip=new_master.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                            target_port=new_master.port,
                        )
                    )

                # 之前切换
                cluster_pipeline.add_act(
                    act_name=_("执行切换"),
                    act_component_code=SqlserverActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            exec_ips=[Host(ip=new_master.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                            get_payload_func=SqlserverActPayload.get_switch_payload.__name__,
                        )
                    ),
                )

                # 变更集群域名映射
                cluster_pipeline.add_sub_pipeline(
                    sub_flow=switch_domain_sub_flow_for_cluster(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        cluster=cluster,
                        old_master=old_master,
                        new_master=new_master,
                    )
                )

                # 删除随机账号
                cluster_pipeline.add_act(
                    act_name=_("drop job user"),
                    act_component_code=SqlserverDropJobUserComponent.code,
                    kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id])),
                )

                act_list.append(cluster_pipeline.build_sub_process(sub_name=_("{}集群互切".format(cluster.name))))

            # 拼接集群维度的子流程
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=act_list)

            # 安装机器维度变更元数据
            sub_pipeline.add_act(
                act_name=_("变更元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.sqlserver_ha_switch.__name__,
                    )
                ),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("切换子流程")))

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
