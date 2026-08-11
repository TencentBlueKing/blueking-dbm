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
from typing import Any, Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import init_machine_sub_flow
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_cluster_apply_summary import (
    MysqlClusterApplySummaryComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_mysql_init_os_timezone_kwargs_for_apply
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_clb_util import build_mysql_clb_apply_subs
from backend.flow.utils.mysql.mysql_context_dataclass import HaApplyManualContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLHAApplyFlow(object):
    """
    构建mysql主从版申请流程的抽象类
    兼容跨云区域的场景支持
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    def __calc_install_ports(self, inst_sum: int = 0) -> Tuple[list, list]:
        """
        计算单据流程需要安装的端口，然后传入到流程的单据信息，ha集群包括有mysql实例和proxy实例
        @param : 代表机器部署实例数量
        """
        install_proxy_ports = []
        install_mysql_ports = []
        for i in range(0, inst_sum):
            install_proxy_ports.append(self.data["start_proxy_port"] + i)
            install_mysql_ports.append(self.data["start_mysql_port"] + i)

        return install_proxy_ports, install_mysql_ports

    def __build_init_os_tz_kwargs(self, exec_ips: list):
        """部署场景专用：根据单据 ticket_data 构造机器时区初始化 kwargs。

        设计要点 / 怎么做：
          - HA 部署阶段集群尚未落库，无法用 ``cluster_id`` 反查 db_meta。本方法从
            ``self.data``（ticket_data）里直接取 ``bk_biz_id / bk_cloud_id / db_module_id``
            三个字段：这三个字段在 :class:`MysqlHAApplyFlowBuilder.patch_ticket_detail`
            阶段已由 dbconfig 预写入。
          - HA 单据下一台机器上即便部署多个 HA 集群（``inst_num``），也共享同一个
            ``db_module_id``（ticket_data 顶层标量），因此机器时区只需按"单一 module"
            调用组件即可。
          - 时区来源已统一为 dbconfig 模块级 ``deploy_info.system_time_zone``，无需
            再关心 ``db_version`` / ``immute_domain`` / ``spider_version``。

        :param exec_ips: 目标机器 IP 列表（去重后传入），非空
        :return: :class:`MySQLInitOsTimeZoneKwargs` 实例

        边界 / 异常：
          - exec_ips 为空 / 单据字段类型不合法 → 由底层
            :func:`get_mysql_init_os_timezone_kwargs_for_apply` 抛异常。
        """
        return get_mysql_init_os_timezone_kwargs_for_apply(
            bk_biz_id=int(self.data["bk_biz_id"]),
            bk_cloud_id=int(self.data["bk_cloud_id"]),
            exec_ip=exec_ips,
            db_module_id=int(self.data["db_module_id"]),
            cluster_type=ClusterType.TenDBHA,
        )

    def _build_apply_summary_clusters(self) -> List[Dict[str, Any]]:
        """基于 ticket_data(``self.data``) 拼装 TenDBHA 集群交付摘要的集群定位信息列表。

        设计要点 / 怎么做：
          - 数据源：``self.data["apply_infos"]``；每条 apply_info 下的 ``clusters`` 是本次
            要交付的集群集合，每个 cluster 至少含 ``master``（主域名）。
          - 本方法**只产出"集群定位信息"**：`{bk_biz_id, cluster_domain}`；其他所有摘要字段
            （access_port / slave DNS / CLB 等）由 :class:`MysqlClusterApplySummaryComponent`
            在运行时从 db_meta 反查装配，flow 侧无需拼装任何"半成品"字段。

        :return: 集群定位信息列表；每项为 `{bk_biz_id: int, cluster_domain: str}`。
                 apply_infos 为空或所有 apply 内 clusters 为空时，返回空列表；
                 摘要 Component 收到空列表会走 no-op 分支，不阻塞流程。

        边界 / 异常：
          - 若 apply_info 中 cluster 缺少 ``master`` -> KeyError。
            注意：本方法在 flow **构建期**同步执行（作为 ``pipeline.add_act`` 的 kwargs 实参），
            并非 pipeline 节点运行期，故异常不会被 ``BaseService.execute`` 捕获，
            会直接冒泡导致整张单据 flow 构建失败。
          - 此处刻意不做防御跳过：``cluster["master"]`` 同时也是主部署流程（如
            ``deploy_mysql_ha_flow_with_manual``）依赖的强契约字段，缺失时主流程本身即无法执行；
            此处快速失败可尽早暴露上游数据契约问题，避免"主流程崩、摘要静默"的诡异状态。
        """
        bk_biz_id: int = int(self.data["bk_biz_id"])
        clusters: List[Dict[str, Any]] = []
        for info in self.data["apply_infos"]:
            for cluster in info.get("clusters", []):
                clusters.append({"bk_biz_id": bk_biz_id, "cluster_domain": cluster["master"]})
        return clusters

    def deploy_mysql_ha_flow_with_manual(self):
        """
        定义部署主从版集群的流程，资源是通过手动录入方式，兼容单机多实例的部署
        """
        mysql_ha_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        instances = []
        for info in self.data["apply_infos"]:
            # 以机器维度并发处理 内容：比如获取对应节点资源、先发介质、初始化机器、安装实例、安装备份进程

            # 拼接子流程需要全局参数
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("apply_infos")

            # 计算机器需要部署的proxy、mysql的端口列表，集群的依据：MIN(多实例上限,映射的cluster集群数量)
            sub_flow_context["proxy_ports"], sub_flow_context["mysql_ports"] = self.__calc_install_ports(
                min(int(sub_flow_context["inst_num"]), len(info["clusters"]))
            )

            instances.extend(
                [
                    "{}:{}".format(ip["ip"], port)
                    for ip in info["proxy_ip_list"]
                    for port in sub_flow_context["proxy_ports"]
                ]
            )
            instances.extend(
                [
                    "{}:{}".format(ip["ip"], port)
                    for ip in info["mysql_ip_list"]
                    for port in sub_flow_context["mysql_ports"]
                ]
            )

            clusters = []
            bk_host_ids = []
            for number, cluster in enumerate(info["clusters"]):
                # 分配部署proxy_port、mysql_port、ip 、cluster的关系
                cluster["new_master_ip"] = info["mysql_ip_list"][0]["ip"]
                cluster["new_slave_ip"] = info["mysql_ip_list"][1]["ip"]
                cluster["new_proxy_1_ip"] = info["proxy_ip_list"][0]["ip"]
                cluster["new_proxy_2_ip"] = info["proxy_ip_list"][1]["ip"]
                cluster["set_backend_ip"] = cluster["new_master_ip"]
                cluster["mysql_port"] = sub_flow_context["mysql_ports"][number]
                cluster["proxy_port"] = sub_flow_context["proxy_ports"][number]
                clusters.append(cluster)
                bk_host_ids.append(info["mysql_ip_list"][0]["bk_host_id"])
                bk_host_ids.append(info["mysql_ip_list"][1]["bk_host_id"])
                bk_host_ids.append(info["proxy_ip_list"][0]["bk_host_id"])
                bk_host_ids.append(info["proxy_ip_list"][1]["bk_host_id"])

            sub_flow_context["clusters"] = clusters

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=int(self.data["bk_cloud_id"]),
                cluster_type=ClusterType.TenDBHA,
            )

            # 初始新机器
            sub_pipeline.add_sub_pipeline(
                sub_flow=init_machine_sub_flow(
                    uid=sub_flow_context["uid"],
                    root_id=self.root_id,
                    bk_cloud_id=int(sub_flow_context["bk_cloud_id"]),
                    sys_init_ips=[ip_info["ip"] for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]],
                    init_check_ips=[ip_info["ip"] for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]],
                    yum_install_perl_ips=[ip_info["ip"] for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]],
                    bk_host_ids=bk_host_ids,
                    # 部署阶段无 db_meta，直接依据单据 ticket_data + 当前 apply_info 组装机器时区初始化 kwargs
                    init_os_tz_kwargs=self.__build_init_os_tz_kwargs(
                        exec_ips=sorted({ip_info["ip"] for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]}),
                    ),
                )
            )

            # 阶段1 并行分发安装文件
            sub_pipeline.add_parallel_acts(
                acts_list=[
                    {
                        "act_name": _("下发MySQL介质包"),
                        "act_component_code": TransFileComponent.code,
                        "kwargs": asdict(
                            DownloadMediaKwargs(
                                bk_cloud_id=int(self.data["bk_cloud_id"]),
                                exec_ip=[ip_info["ip"] for ip_info in info["mysql_ip_list"]],
                                file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                                    db_version=self.data["db_version"]
                                ),
                            )
                        ),
                    },
                    {
                        "act_name": _("下发Proxy介质包"),
                        "act_component_code": TransFileComponent.code,
                        "kwargs": asdict(
                            DownloadMediaKwargs(
                                bk_cloud_id=int(self.data["bk_cloud_id"]),
                                exec_ip=[ip_info["ip"] for ip_info in info["proxy_ip_list"]],
                                file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_install_package(),
                            )
                        ),
                    },
                ]
            )

            # 阶段3 并发安装mysql、proxy 实例(一个活动节点部署多实例)
            acts_list = []
            for proxy_ip in info["proxy_ip_list"]:
                exec_act_kwargs.exec_ip = proxy_ip["ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_proxy_for_deploy_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("安装proxy实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            for mysql_ip in info["mysql_ip_list"]:
                exec_act_kwargs.exec_ip = mysql_ip["ip"]
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_mysql_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("安装MySQL实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                        "write_payload_var": HaApplyManualContext.get_time_zone_var_name(),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段4 以集群维度并发处理 集群内容：比如建立主从、proxy实例配置后端、添加对应的域名等步骤
            build_cluster_sub_list = []
            for cluster in sub_flow_context["clusters"]:

                # 拼接子流程需要全局参数
                cluster_sub_flow_context = copy.deepcopy(self.data)
                cluster_sub_flow_context.pop("apply_infos")

                # 声明子流程
                cluster_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(cluster_sub_flow_context))

                # 拼接子流程支持原子任务的活动节点需要的通用的私有参数结构体
                cluster_act_kwargs = ExecActuatorKwargs(bk_cloud_id=int(self.data["bk_cloud_id"]), cluster=cluster)

                cluster_act_kwargs.exec_ip = cluster["new_master_ip"]
                cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_mysql_repl_user_payload.__name__
                cluster_sub_pipeline.add_act(
                    act_name=_("新增repl帐户"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(cluster_act_kwargs),
                    write_payload_var=HaApplyManualContext.get_sync_info_var_name(),
                )

                cluster_act_kwargs.exec_ip = cluster["new_slave_ip"]
                cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_change_master_payload.__name__
                cluster_sub_pipeline.add_act(
                    act_name=_("建立主从关系"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(cluster_act_kwargs),
                )

                acts_list = []
                for proxy_ip in [cluster["new_proxy_1_ip"], cluster["new_proxy_2_ip"]]:
                    cluster_act_kwargs.exec_ip = proxy_ip
                    cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_set_proxy_backends.__name__
                    acts_list.append(
                        {
                            "act_name": _("proxy配置后端实例"),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(cluster_act_kwargs),
                        }
                    )
                cluster_sub_pipeline.add_parallel_acts(acts_list=acts_list)

                cluster_sub_pipeline.add_parallel_acts(
                    acts_list=[
                        {
                            "act_name": _("添加主集群域名"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=self.data["bk_cloud_id"],
                                    add_domain_name=cluster["master"],
                                    dns_op_exec_port=cluster["proxy_port"],
                                    exec_ip=[cluster["new_proxy_1_ip"], cluster["new_proxy_2_ip"]],
                                )
                            ),
                        },
                        {
                            "act_name": _("添加从集群域名"),
                            "act_component_code": MySQLDnsManageComponent.code,
                            "kwargs": asdict(
                                CreateDnsKwargs(
                                    bk_cloud_id=self.data["bk_cloud_id"],
                                    add_domain_name=cluster["slave"],
                                    dns_op_exec_port=cluster["mysql_port"],
                                    exec_ip=cluster["new_slave_ip"],
                                )
                            ),
                        },
                    ]
                )

                build_cluster_sub_list.append(
                    cluster_sub_pipeline.build_sub_process(sub_name=_("{}集群部署").format(cluster["name"]))
                )

            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=build_cluster_sub_list)

            # 阶段6 拼接db-meta的新ip信息到私有变量cluster,为了兼容机器属于多组cluster的录入场景，clusters信息通过子流程的上下文获取即可
            machine_info = {
                "new_master_ip": info["mysql_ip_list"][0]["ip"],
                "new_slave_ip": info["mysql_ip_list"][1]["ip"],
                "new_proxy_1_ip": info["proxy_ip_list"][0]["ip"],
                "new_proxy_2_ip": info["proxy_ip_list"][1]["ip"],
            }

            sub_pipeline.add_act(
                act_name=_("更新DBMeta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.mysql_ha_apply.__name__,
                        cluster=machine_info,
                        is_update_trans_data=True,
                    )
                ),
            )

            # 部署成功后按单据传参创建CLB（依赖元数据已落库，执行态按主域名解析cluster_id）
            clb_sub_list = []
            for cluster in sub_flow_context["clusters"]:
                clb_sub_list.extend(
                    build_mysql_clb_apply_subs(
                        root_id=self.root_id,
                        data=copy.deepcopy(sub_flow_context),
                        bk_biz_id=self.data["bk_biz_id"],
                        domain_name=cluster["master"],
                        creator=self.data["created_by"],
                        apply_clb=self.data.get("apply_clb", False),
                    )
                )
            if clb_sub_list:
                sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=clb_sub_list)

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("部署MySQL高可用集群")))

        mysql_ha_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 所有集群部署完成后集中标准化
        mysql_ha_pipeline.add_sub_pipeline(
            sub_flow=standardize_mysql_cluster_subflow(
                root_id=self.root_id,
                data=copy.deepcopy(self.data),
                bk_cloud_id=self.data["bk_cloud_id"],
                bk_biz_id=self.data["bk_biz_id"],
                instances=instances,
                with_actuator=False,
                with_bk_plugin=False,
                with_probe=True,
            )
        )

        # 写入集群交付摘要：db_meta 已由"更新DBMeta元信息"节点写入，此处只需传集群定位信息，
        # 主入口端口 / slave 只读入口 / CLB 等运行时字段由 Component 从 db_meta 反查装配；
        # 幂等由 ClusterApplySummarySerializer.table_primary_key = "cluster_domain_and_port" 保证。
        mysql_ha_pipeline.add_act(
            act_name=_("写入集群交付摘要"),
            act_component_code=MysqlClusterApplySummaryComponent.code,
            kwargs={"clusters": self._build_apply_summary_clusters()},
            is_remote_rewritable=True,
        )

        mysql_ha_pipeline.run_pipeline(init_trans_data_class=HaApplyManualContext())
