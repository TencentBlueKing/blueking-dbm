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
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import install_surrounding_apps_sub_flow
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.mysql.mysql_act_dataclass import CreateDnsKwargs
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverStandardizationFlow(BaseFlow):
    """
    构建Sqlserver集群录入标准化流程
    """

    def run_flow(self):
        """
        定义构建Sqlserver集群录入标准化流程，支持多集群并发执行
        流程步骤：
        1：集群维度录入元数据
        2：添加初始化账号
        3：重建系统库monitor
        4：部署周边程序（录入配置信息，按照backup_client）
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:

            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context.update({"master_ip": info["mssql_master_host"]["ip"]})
            sub_flow_context.update({"slave_ip": info["mssql_slave_host"]["ip"]})

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_context)

            if info["is_ha"]:
                # 主从
                target_hosts = [Host(**info["mssql_master_host"]), Host(**info["mssql_slave_host"])]
                db_meta_class_func = SqlserverDBMeta.sqlserver_ha_apply.__name__
            else:
                # 单节点
                target_hosts = [Host(**info["mssql_master_host"])]
                db_meta_class_func = SqlserverDBMeta.sqlserver_single_apply.__name__

            # 主机维度下发执行器
            sub_pipeline.add_act(
                act_name=_("下发执行器"),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=target_hosts,
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )

            # 集群维度处理标准化
            act_list = []
            for cluster in info["clusters"]:
                cluster_sub_flow_context = copy.deepcopy(self.data)
                cluster_sub_flow_context.pop("infos")

                # 声明子流程
                cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(cluster_sub_flow_context))

                # 主从实例接入初始化
                init_acts_list = []
                for host in target_hosts:
                    init_acts_list.append(
                        {
                            "act_name": _("实例接入标准化[{}:{}]".format(host.ip, cluster["port"])),
                            "act_component_code": SqlserverActuatorScriptComponent.code,
                            "kwargs": asdict(
                                ExecActuatorKwargs(
                                    exec_ips=[host],
                                    get_payload_func=SqlserverActPayload.init_instance_for_dbm.__name__,
                                    custom_params={"port": cluster["port"]},
                                ),
                            ),
                        }
                    )
                cluster_sub_pipeline.add_parallel_acts(acts_list=init_acts_list)

                # 是否添加对应域名
                dns_acts_list = []
                if cluster["is_add_immutable_domain"]:
                    dns_acts_list.append(
                        {
                            "act_name": _("添加域名{}".format(cluster["immutable_domain"])),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=info["mssql_master_host"]["bk_cloud_id"],
                                    add_domain_name=cluster["immutable_domain"],
                                    dns_op_exec_port=cluster["port"],
                                    exec_ip=info["mssql_master_host"]["ip"],
                                )
                            ),
                        },
                    )
                if cluster["is_add_slave_domain"]:
                    dns_acts_list.append(
                        {
                            "act_name": _("添加域名{}".format(cluster["slave_domain"])),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=info["mssql_slave_host"]["bk_cloud_id"],
                                    add_domain_name=cluster["slave_domain"],
                                    dns_op_exec_port=cluster["port"],
                                    exec_ip=info["mssql_slave_host"]["ip"],
                                )
                            ),
                        },
                    )
                if len(dns_acts_list) > 0:
                    cluster_sub_pipeline.add_parallel_acts(acts_list=dns_acts_list)

                act_list.append(
                    cluster_sub_pipeline.build_sub_process(sub_name=_("集群标准化[{}]".format(cluster["name"])))
                )
            # 拼接集群维度的子流程
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=act_list)

            # 录入集群元数据，同组机器作为原子任务同时录入
            sub_pipeline.add_act(
                act_name=_("录入db_meta元信息"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=db_meta_class_func)),
            )

            # 安装周边程序
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_surrounding_apps_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    bk_biz_id=int(sub_flow_context["bk_biz_id"]),
                    bk_cloud_id=int(sub_flow_context["bk_cloud_id"]),
                    master_host=[Host(**info["mssql_master_host"])],
                    slave_host=[Host(**info["mssql_slave_host"])] if info["is_ha"] else [],
                    cluster_domain_list=[c["immutable_domain"] for c in info["clusters"]],
                    is_get_old_backup_config=True,
                )
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("集群标准化")))

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline()
