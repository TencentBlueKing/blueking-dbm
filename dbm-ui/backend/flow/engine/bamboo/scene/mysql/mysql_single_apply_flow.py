# -*- coding: utf-8 -*-
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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_surrounding_apps_sub_flow,
    init_machine_sub_flow,
)
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SingleApplyManualContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLSingleApplyFlow(object):
    """
    构建mysql单节点申请流程的抽象类
    兼容跨云区域的场景支持
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __calc_install_ports(self, inst_sum: int = 0) -> list:
        """
        计算单据流程需要安装的端口，然后传入到流程的单据信息，single集群只有mysql实例
        @param inst_sum: 代表机器部署实例数量
        """
        install_mysql_ports = []
        for i in range(0, inst_sum):
            install_mysql_ports.append(self.data["start_mysql_port"] + i)

        return install_mysql_ports

    def deploy_mysql_single_flow_with_manual(self):
        """
        定义部署单节点集群的流程，资源是通过手动录入方式，兼容单机多实例的部署
        目前资源池已经在saas层适配，目前flow统一为手动模式即可
        """

        mysql_single_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["apply_infos"]:
            # 以机器维度并发处理 内容：比如获取对应节点资源、先发介质、初始化机器、安装实例、安装备份进程

            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("apply_infos")

            # 计算机器需要部署的mysql的端口列表，集群的依据：MIN(多实例上限,映射的cluster集群数量)
            sub_flow_context["mysql_ports"] = self.__calc_install_ports(
                min(int(sub_flow_context["inst_num"]), len(info["clusters"]))
            )

            clusters = []
            for number, cluster in enumerate(info["clusters"]):
                # 分配部署mysql_port、ip 、cluster的关系
                cluster["new_ip"] = info["new_ip"]["ip"]
                cluster["mysql_port"] = sub_flow_context["mysql_ports"][number]
                clusters.append(cluster)
            sub_flow_context["clusters"] = clusters

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 声明执行活动节点的公用对象
            exec_act_kwargs = ExecActuatorKwargs(
                exec_ip=info["new_ip"]["ip"],
                cluster_type=ClusterType.TenDBSingle,
                bk_cloud_id=int(self.data["bk_cloud_id"]),
            )

            # 初始新机器
            # 初始新机器
            sub_pipeline.add_sub_pipeline(
                sub_flow=init_machine_sub_flow(
                    uid=sub_flow_context["uid"],
                    root_id=self.root_id,
                    bk_cloud_id=int(sub_flow_context["bk_cloud_id"]),
                    sys_init_ips=[info["new_ip"]["ip"]],
                    init_check_ips=[info["new_ip"]["ip"]],
                    yum_install_perl_ips=[info["new_ip"]["ip"]],
                    bk_host_ids=[info["new_ip"]["bk_host_id"]],
                )
            )

            sub_pipeline.add_act(
                act_name=_("下发MySQL介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=int(self.data["bk_cloud_id"]),
                        exec_ip=info["new_ip"]["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                            db_version=self.data["db_version"]
                        ),
                    )
                ),
            )

            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
            sub_pipeline.add_act(
                act_name=_("部署mysql-crond"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_mysql_payload.__name__
            sub_pipeline.add_act(
                act_name=_("安装MySQL实例"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
                write_payload_var=SingleApplyManualContext.get_time_zone_var_name(),
            )

            dns_act_list = []
            for cluster in sub_flow_context["clusters"]:
                # 以集群维度并发处理 集群内容：比如添加对应的域名
                dns_act_list.append(
                    {
                        "act_name": _("添加集群域名"),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            CreateDnsKwargs(
                                bk_cloud_id=self.data["bk_cloud_id"],
                                add_domain_name=cluster["master"],
                                dns_op_exec_port=cluster["mysql_port"],
                                exec_ip=info["new_ip"]["ip"],
                            )
                        ),
                    }
                )

            sub_pipeline.add_parallel_acts(acts_list=dns_act_list)

            # 拼接db-meta的新ip信息私有变量cluster,为了兼容机器属于多组cluster的录入场景，clusters信息通过子流程的上下文获取即可
            sub_pipeline.add_act(
                act_name=_("录入db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_single_apply.__name__,
                        cluster={"new_ip": info["new_ip"]["ip"]},
                        is_update_trans_data=True,
                    )
                ),
            )

            # 阶段7 部署周边组件
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_surrounding_apps_sub_flow(
                    bk_cloud_id=int(self.data["bk_cloud_id"]),
                    master_ip_list=[info["new_ip"]["ip"]],
                    root_id=self.root_id,
                    parent_global_data=copy.deepcopy(sub_flow_context),
                    is_init=True,
                    collect_sysinfo=True,
                    cluster_type=ClusterType.TenDBSingle.value,
                )
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("部署单节点集群")))

        mysql_single_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        mysql_single_pipeline.run_pipeline(init_trans_data_class=SingleApplyManualContext())
