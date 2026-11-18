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
import shlex
from dataclasses import asdict
from typing import Dict, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend import env
from backend.components.dbresource.client import DBResourceApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.constants import FailoverDrillVersion, failover_drill_has_v2
from backend.db_services.cmdb.biz import get_or_create_resource_module, get_resource_biz
from backend.exceptions import AppBaseException
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.failover_drill_flow import FailoverDrillFlow, append_dbha_trigger_acts
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import init_machine_sub_flow
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.plugins.components.collections.common.external_service import ExternalServiceComponent
from backend.flow.plugins.components.collections.common.transfer_host_service import TransferHostServiceComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.failover_drill_v1 import (
    DrillClusterDecommissionComponent,
    DrillClusterDnsDeleteComponent,
    DrillDbhaReportComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.failover_drill_dbha import get_dbha_v2_service_ips
from backend.flow.utils.mysql.common.mysql_cluster_info import get_mysql_init_os_timezone_kwargs_for_apply
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import HaApplyManualContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.ticket.constants import TicketType


def build_dbha_iptables_scripts(bk_cloud_id: int, logical_city_id: int, cluster_type: str) -> Tuple[str, str]:
    """在申请机器之前解析 DBHA 的屏蔽和清理命令。清理命令删除失败也继续。"""
    drill = FailoverDrillFlow(root_id="iptables", data={"bk_biz_id": 0})
    add_cmd = drill.get_add_shell_script(
        {
            "cluster_type": cluster_type,
            "bk_cloud_id": bk_cloud_id,
            "logical_city_id": logical_city_id,
        }
    )
    parts = [part.strip() for part in drill.get_clean_shell_script().split(";") if part.strip()]
    clean_cmd = "; ".join("{} || true".format(part) for part in parts)
    return add_cmd, clean_cmd


def build_dbha_trigger_scripts(
    bk_cloud_id: int, logical_city_id: int, cluster_type: str, version: str
) -> Tuple[str, str]:
    """申请机器前解析触发命令。v2 先确认总开关和服务 IP，避免机器已经拿下来才发现触发不了。"""
    if failover_drill_has_v2(version):
        if not env.ENABLE_DBHA_V2:
            raise AppBaseException(_("ENABLE_DBHA_V2 未开启，无法执行 dbha-v2 容灾演练"))
        service_ips = get_dbha_v2_service_ips(bk_cloud_id, logical_city_id)
        if not service_ips:
            raise AppBaseException(_("拿不到 dbha-v2 服务 IP，退出演练"))
        trigger = FailoverDrillFlow.get_v2_trigger_script(service_ips)
        clean = "; ".join("iptables -D INPUT -s {} -j DROP || true".format(shlex.quote(ip)) for ip in service_ips)
        return trigger, clean
    return build_dbha_iptables_scripts(bk_cloud_id, logical_city_id, cluster_type)


class MysqlFailoverDrillV1Flow(object):
    """
    TenDBHA 容灾演练独立流程。

    上架节点从 MySQLHAApplyFlow 抄过来，DBHA 触发从 FailoverDrillFlow 抄过来。
    不跑禁用：禁用的连接检查会把系统进程当成业务连接。
    DBHA 是否切换成功都不影响后面的下架、清元数据、带标签退回资源池。
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def run(self):
        """一座城市一条 flow。data 就是这座城市的单据。"""
        pipeline = Builder(root_id=self.root_id, data=self.data)
        pipeline.add_sub_pipeline(self._build_city_subflow(self.data))
        pipeline.run_pipeline(init_trans_data_class=HaApplyManualContext(), is_drop_random_user=False)

    def _build_city_subflow(self, city: Dict):
        city_data = copy.deepcopy(city)
        city_data["force"] = True
        city_data["ticket_type"] = TicketType.MYSQL_FAILOVER_DRILL.value
        sub_pipeline = SubBuilder(root_id=self.root_id, data=city_data)
        sub_pipeline.add_sub_pipeline(self._build_apply_subflow(city_data))
        for drill_flow in self._build_drill_subflows(city_data):
            sub_pipeline.add_sub_pipeline(drill_flow)
        self._add_teardown(sub_pipeline, city_data)
        self._add_return_resource(sub_pipeline, city_data)
        return sub_pipeline.build_sub_process(sub_name=_("容灾演练 {} {}").format(city["city"], city["main_task_id"]))

    def _build_apply_subflow(self, city_data: Dict):
        """上架节点抄自 MySQLHAApplyFlow.deploy_mysql_ha_flow_with_manual，不申请 CLB。"""
        apply_data = copy.deepcopy(city_data)
        apply_data["ticket_type"] = TicketType.MYSQL_HA_APPLY.value
        info = apply_data["apply_infos"][0]
        apply_data.pop("apply_infos")
        proxy_ports, mysql_ports = self._calc_ports(apply_data, len(info["clusters"]))
        apply_data["proxy_ports"] = proxy_ports
        apply_data["mysql_ports"] = mysql_ports

        instances = ["{}:{}".format(ip["ip"], port) for ip in info["proxy_ip_list"] for port in proxy_ports]
        instances.extend("{}:{}".format(ip["ip"], port) for ip in info["mysql_ip_list"] for port in mysql_ports)

        clusters = []
        bk_host_ids = []
        for number, cluster in enumerate(info["clusters"]):
            cluster["new_master_ip"] = info["mysql_ip_list"][0]["ip"]
            cluster["new_slave_ip"] = info["mysql_ip_list"][1]["ip"]
            cluster["new_proxy_1_ip"] = info["proxy_ip_list"][0]["ip"]
            cluster["new_proxy_2_ip"] = info["proxy_ip_list"][1]["ip"]
            cluster["set_backend_ip"] = cluster["new_master_ip"]
            cluster["mysql_port"] = mysql_ports[number]
            cluster["proxy_port"] = proxy_ports[number]
            clusters.append(cluster)
            bk_host_ids.extend(
                [
                    info["mysql_ip_list"][0]["bk_host_id"],
                    info["mysql_ip_list"][1]["bk_host_id"],
                    info["proxy_ip_list"][0]["bk_host_id"],
                    info["proxy_ip_list"][1]["bk_host_id"],
                ]
            )
        apply_data["clusters"] = clusters

        sub_pipeline = SubBuilder(root_id=self.root_id, data=apply_data)
        exec_ips = [ip_info["ip"] for ip_info in info["mysql_ip_list"] + info["proxy_ip_list"]]
        sub_pipeline.add_sub_pipeline(
            sub_flow=init_machine_sub_flow(
                uid=apply_data["uid"],
                root_id=self.root_id,
                bk_cloud_id=int(apply_data["bk_cloud_id"]),
                sys_init_ips=exec_ips,
                init_check_ips=exec_ips,
                yum_install_perl_ips=exec_ips,
                bk_host_ids=bk_host_ids,
                init_os_tz_kwargs=get_mysql_init_os_timezone_kwargs_for_apply(
                    bk_biz_id=int(apply_data["bk_biz_id"]),
                    bk_cloud_id=int(apply_data["bk_cloud_id"]),
                    exec_ip=sorted(set(exec_ips)),
                    db_module_id=int(apply_data["db_module_id"]),
                    cluster_type=ClusterType.TenDBHA,
                ),
            )
        )

        sub_pipeline.add_parallel_acts(
            acts_list=[
                {
                    "act_name": _("下发MySQL介质包"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=int(apply_data["bk_cloud_id"]),
                            exec_ip=[ip_info["ip"] for ip_info in info["mysql_ip_list"]],
                            file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                                db_version=apply_data["db_version"]
                            ),
                        )
                    ),
                },
                {
                    "act_name": _("下发Proxy介质包"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=int(apply_data["bk_cloud_id"]),
                            exec_ip=[ip_info["ip"] for ip_info in info["proxy_ip_list"]],
                            file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_install_package(),
                        )
                    ),
                },
            ]
        )

        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=int(apply_data["bk_cloud_id"]),
            cluster_type=ClusterType.TenDBHA,
            cluster={},
        )
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

        cluster_sub_list = []
        for cluster in clusters:
            cluster_data = copy.deepcopy(apply_data)
            cluster_sub = SubBuilder(root_id=self.root_id, data=cluster_data)
            cluster_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=int(apply_data["bk_cloud_id"]),
                cluster=cluster,
            )
            cluster_act_kwargs.exec_ip = cluster["new_master_ip"]
            cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_grant_mysql_repl_user_payload.__name__
            cluster_sub.add_act(
                act_name=_("新增repl帐户"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(cluster_act_kwargs),
                write_payload_var=HaApplyManualContext.get_sync_info_var_name(),
            )
            cluster_act_kwargs.exec_ip = cluster["new_slave_ip"]
            cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_change_master_payload.__name__
            cluster_sub.add_act(
                act_name=_("建立主从关系"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(cluster_act_kwargs),
            )
            proxy_acts = []
            for proxy_ip in [cluster["new_proxy_1_ip"], cluster["new_proxy_2_ip"]]:
                cluster_act_kwargs.exec_ip = proxy_ip
                cluster_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_set_proxy_backends.__name__
                proxy_acts.append(
                    {
                        "act_name": _("proxy配置后端实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(cluster_act_kwargs),
                    }
                )
            cluster_sub.add_parallel_acts(acts_list=proxy_acts)
            cluster_sub.add_parallel_acts(
                acts_list=[
                    {
                        "act_name": _("添加主集群域名"),
                        "act_component_code": MySQLDnsManageComponent.code,
                        "kwargs": asdict(
                            CreateDnsKwargs(
                                bk_cloud_id=apply_data["bk_cloud_id"],
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
                                bk_cloud_id=apply_data["bk_cloud_id"],
                                add_domain_name=cluster["slave"],
                                dns_op_exec_port=cluster["mysql_port"],
                                exec_ip=cluster["new_slave_ip"],
                            )
                        ),
                    },
                ]
            )
            cluster_sub_list.append(cluster_sub.build_sub_process(sub_name=_("{}集群部署").format(cluster["name"])))
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_sub_list)

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
        sub_pipeline.add_sub_pipeline(
            sub_flow=standardize_mysql_cluster_subflow(
                root_id=self.root_id,
                data=copy.deepcopy(apply_data),
                bk_cloud_id=apply_data["bk_cloud_id"],
                bk_biz_id=apply_data["bk_biz_id"],
                instances=instances,
                with_actuator=False,
                with_bk_plugin=False,
                with_probe=True,
            )
        )
        return sub_pipeline.build_sub_process(sub_name=_("上架TenDBHA演练集群"))

    def _build_drill_subflows(self, city_data: Dict) -> List:
        """先 backend 再 proxy，和旧演练 types 顺序一致。"""
        subs = []
        drill_ips = city_data["drill_ips"]
        for role in ("backend", "proxy"):
            ip = drill_ips[role]
            drill = SubBuilder(root_id=self.root_id, data=copy.deepcopy(city_data))
            append_dbha_trigger_acts(drill, self.root_id, city_data, role, ip)
            subs.append(drill.build_sub_process(sub_name=_("触发DBHA {}").format(role)))
        return subs

    def _add_teardown(self, sub_pipeline: SubBuilder, city_data: Dict):
        """下架节点抄自 MySQLHADestroyFlow。不做禁用的连接检查。删域名、卸载实例、清元数据失败会停住。"""
        info = city_data["apply_infos"][0]
        mysql_ips = [ip["ip"] for ip in info["mysql_ip_list"]]
        proxy_ips = [ip["ip"] for ip in info["proxy_ip_list"]]
        mysql_port = int(city_data["start_mysql_port"])
        proxy_port = int(city_data["start_proxy_port"])
        cluster = {
            "backend_port": mysql_port,
            "proxy_port": proxy_port,
            "backend_ip_list": mysql_ips,
            "proxy_ip_list": proxy_ips,
            "bk_cloud_id": city_data["bk_cloud_id"],
        }
        domain = info["clusters"][0]["master"]
        slave_domain = info["clusters"][0].get("slave") or ""
        sub_pipeline.add_act(
            act_name=_("删除演练域名"),
            act_component_code=DrillClusterDnsDeleteComponent.code,
            kwargs={
                "bk_biz_id": city_data["bk_biz_id"],
                "bk_cloud_id": city_data["bk_cloud_id"],
                "immute_domain": domain,
                "slave_domain": slave_domain,
            },
        )
        sub_pipeline.add_act(
            act_name=_("下发db-actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=city_data["bk_cloud_id"],
                    exec_ip=mysql_ips + proxy_ips,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
            error_ignorable=True,
        )

        exec_act_kwargs = ExecActuatorKwargs(bk_cloud_id=int(city_data["bk_cloud_id"]), cluster=cluster)
        proxy_acts = []
        for proxy_ip in proxy_ips:
            exec_act_kwargs.exec_ip = proxy_ip
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_surrounding_config_payload.__name__
            exec_act_kwargs.component_kwargs = {}
            proxy_acts.append(
                {
                    "act_name": _("清理实例周边配置"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                    "error_ignorable": True,
                }
            )
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_proxy_payload.__name__
            exec_act_kwargs.component_kwargs = {"proxy_port": proxy_port, "force": True}
            proxy_acts.append(
                {
                    "act_name": _("卸载proxy实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=proxy_acts)

        mysql_acts = []
        for mysql_ip in mysql_ips:
            exec_act_kwargs.exec_ip = mysql_ip
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_surrounding_config_payload.__name__
            exec_act_kwargs.component_kwargs = {}
            mysql_acts.append(
                {
                    "act_name": _("清理实例周边配置"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                    "error_ignorable": True,
                }
            )
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_mysql_payload.__name__
            exec_act_kwargs.component_kwargs = {}
            mysql_acts.append(
                {
                    "act_name": _("卸载mysql实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=mysql_acts)

        sub_pipeline.add_act(
            act_name=_("清理db_meta元信息"),
            act_component_code=DrillClusterDecommissionComponent.code,
            kwargs={
                "bk_biz_id": city_data["bk_biz_id"],
                "bk_cloud_id": city_data["bk_cloud_id"],
                "immute_domain": domain,
            },
        )
        exec_act_kwargs.exec_ip = mysql_ips + proxy_ips
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
        exec_act_kwargs.component_kwargs = {}
        sub_pipeline.add_act(
            act_name=_("清理机器级别配置"),
            act_component_code=MySQLClearMachineComponent.code,
            kwargs=asdict(exec_act_kwargs),
            error_ignorable=True,
        )
        sub_pipeline.add_act(
            act_name=_("记录DBHA切换结果"),
            act_component_code=DrillDbhaReportComponent.code,
            kwargs={
                "main_task_id": city_data["main_task_id"],
                "bk_biz_id": city_data["bk_biz_id"],
                "bk_cloud_id": city_data["bk_cloud_id"],
                "drill_ips": city_data["drill_ips"],
                "dbha_version": city_data.get("dbha_version") or FailoverDrillVersion.V1.value,
            },
            error_ignorable=True,
        )

    def _add_return_resource(self, sub_pipeline: SubBuilder, city_data: Dict):
        labels = city_data.get("labels") or []
        hosts = city_data["hosts"]
        import_data = {
            "resource_type": "mysql",
            "for_biz": city_data["bk_biz_id"],
            "bk_biz_id": get_resource_biz(),
            "hosts": hosts,
            "labels": labels,
            "task_id": city_data["main_task_id"],
            "bill_id": city_data["main_task_id"],
            "bill_type": "RESOURCE_IMPORT",
            "operator": "dba",
        }
        sub_pipeline.add_act(
            act_name=_("机器归还资源池并打标签 {}").format(",".join(labels)),
            act_component_code=ExternalServiceComponent.code,
            kwargs={
                "params": import_data,
                "api_import_path": DBResourceApi.__module__,
                "api_import_module": "DBResourceApi",
                "api_call_func": "resource_import",
            },
        )
        sub_pipeline.add_act(
            act_name=_("主机转移至资源池空闲模块"),
            act_component_code=TransferHostServiceComponent.code,
            kwargs={
                "bk_biz_id": get_resource_biz(),
                "bk_module_ids": [get_or_create_resource_module()],
                "bk_host_ids": [host["host_id"] for host in hosts],
                "update_host_properties": {"dbm_meta": [], "need_monitor": False, "update_operator": False},
            },
        )

    @staticmethod
    def _calc_ports(data: Dict, cluster_count: int) -> Tuple[List[int], List[int]]:
        inst_sum = min(int(data["inst_num"]), cluster_count)
        proxy_ports = []
        mysql_ports = []
        for index in range(inst_sum):
            proxy_ports.append(int(data["start_proxy_port"]) + index)
            mysql_ports.append(int(data["start_mysql_port"]) + index)
        return proxy_ports, mysql_ports
