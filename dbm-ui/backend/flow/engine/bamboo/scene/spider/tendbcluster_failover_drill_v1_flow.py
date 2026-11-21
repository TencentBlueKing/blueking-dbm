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
from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.constants import FailoverDrillVersion
from backend.db_services.cmdb.biz import get_or_create_resource_module, get_resource_biz
from backend.flow.consts import TDBCTL_USER, PrivRole
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.failover_drill_flow import append_dbha_trigger_acts
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_repl_by_manual_input_sub_flow,
    init_machine_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.plugins.components.collections.common.external_service import ExternalServiceComponent
from backend.flow.plugins.components.collections.common.transfer_host_service import TransferHostServiceComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import SpiderRemoteClearMachineComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.failover_drill_v1 import (
    DrillClusterDecommissionComponent,
    DrillClusterDnsDeleteComponent,
    DrillDbhaReportComponent,
)
from backend.flow.plugins.components.collections.mysql.sync_master import SyncMasterComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.add_system_user_in_cluster import (
    AddSystemUserInClusterComponent,
)
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.base.base_dataclass import Instance
from backend.flow.utils.mysql.common.mysql_cluster_info import get_mysql_init_os_timezone_kwargs_for_apply
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSpiderSystemUserKwargs,
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    MysqlSyncMasterKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SpiderApplyManualContext
from backend.flow.utils.spider.spider_act_dataclass import InstanceTuple, ShardInfo
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.ticket.constants import TicketType

DRILL_SHARD_NUM = 2


class TendbClusterFailoverDrillV1Flow(object):
    """
    TenDBCluster 容灾演练独立流程。

    上架节点从 TenDBClusterApplyFlow.deploy_cluster 抄过来，不申请 CLB，不写交付摘要。
    不跑禁用。DBHA 是否切换成功都不影响后面的下架、清元数据、带标签退回资源池。
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def run(self):
        """一座城市一条 flow。data 就是这座城市的单据。"""
        pipeline = Builder(root_id=self.root_id, data=self.data)
        pipeline.add_sub_pipeline(self._build_city_subflow(self.data))
        pipeline.run_pipeline(init_trans_data_class=SpiderApplyManualContext(), is_drop_random_user=False)

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
        """上架节点抄自 TenDBClusterApplyFlow.deploy_cluster。"""
        apply_data = copy.deepcopy(city_data)
        apply_data["ticket_type"] = TicketType.TENDBCLUSTER_APPLY.value
        apply_data["clusters"] = []
        apply_data["enable_tokudb"] = False
        apply_data["ctl_charset"] = apply_data["charset"]
        apply_data["spider_charset"] = apply_data["charset"]
        apply_data["spider_ports"] = [int(apply_data["spider_port"])]
        apply_data["ctl_port"] = int(apply_data["spider_port"]) + 1000
        apply_data["mysql_ip_list"] = []
        for group in apply_data["remote_group"]:
            apply_data["mysql_ip_list"].append(group["master"])
            apply_data["mysql_ip_list"].append(group["slave"])
        mysql_ports = []
        for index in range(int(apply_data["remote_shard_num"])):
            port = int(apply_data["start_mysql_port"]) + index
            mysql_ports.append(port)
            apply_data["clusters"].append({"mysql_port": port, "master": apply_data["immutable_domain"]})
        apply_data["mysql_ports"] = mysql_ports
        tdbctl_pass = get_random_string(length=10)

        sub_pipeline = SubBuilder(root_id=self.root_id, data=apply_data)
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=int(apply_data["bk_cloud_id"]),
            cluster_type=ClusterType.TenDBCluster,
            cluster={},
        )
        all_ips = apply_data["mysql_ip_list"] + apply_data["spider_ip_list"]
        ip_list = [ip_info["ip"] for ip_info in all_ips]
        sub_pipeline.add_sub_pipeline(
            sub_flow=init_machine_sub_flow(
                uid=apply_data["uid"],
                root_id=self.root_id,
                bk_cloud_id=int(apply_data["bk_cloud_id"]),
                sys_init_ips=ip_list,
                init_check_ips=ip_list,
                yum_install_perl_ips=ip_list,
                bk_host_ids=[ip_info["bk_host_id"] for ip_info in all_ips],
                init_os_tz_kwargs=get_mysql_init_os_timezone_kwargs_for_apply(
                    bk_biz_id=int(apply_data["bk_biz_id"]),
                    bk_cloud_id=int(apply_data["bk_cloud_id"]),
                    exec_ip=sorted(set(ip_list)),
                    db_module_id=int(apply_data["db_module_id"]),
                    cluster_type=ClusterType.TenDBCluster.value,
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
                            exec_ip=[ip_info["ip"] for ip_info in apply_data["mysql_ip_list"]],
                            file_list=GetFileList(db_type=DBType.MySQL).mysql_install_package(
                                db_version=apply_data["db_version"]
                            ),
                        )
                    ),
                },
                {
                    "act_name": _("下发Spider/tdbCtl介质包"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=int(apply_data["bk_cloud_id"]),
                            exec_ip=[ip_info["ip"] for ip_info in apply_data["spider_ip_list"]],
                            file_list=GetFileList(db_type=DBType.MySQL).spider_master_install_package(
                                spider_version=apply_data["spider_version"]
                            ),
                        )
                    ),
                },
            ]
        )

        exec_act_kwargs.cluster = {"old_instance_configs": {}}
        mysql_acts = []
        for mysql_ip in apply_data["mysql_ip_list"]:
            exec_act_kwargs.exec_ip = mysql_ip["ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_mysql_payload.__name__
            mysql_acts.append(
                {
                    "act_name": _("安装MySQL实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                    "write_payload_var": SpiderApplyManualContext.get_time_zone_var_name(),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=mysql_acts)

        spider_acts = []
        auto_incr_value = 1
        for spider_ip in apply_data["spider_ip_list"]:
            exec_act_kwargs.exec_ip = spider_ip["ip"]
            exec_act_kwargs.cluster = {
                "immutable_domain": apply_data["immutable_domain"],
                "auto_incr_value": auto_incr_value,
                "spider_copy_config": {},
            }
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_spider_payload.__name__
            spider_acts.append(
                {
                    "act_name": _("安装Spider实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
            auto_incr_value += 1
        sub_pipeline.add_parallel_acts(acts_list=spider_acts)

        ctl_acts = []
        for ctl_ip in apply_data["spider_ip_list"]:
            exec_act_kwargs.exec_ip = ctl_ip["ip"]
            exec_act_kwargs.cluster = {"immutable_domain": apply_data["immutable_domain"]}
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_spider_ctl_payload.__name__
            ctl_acts.append(
                {
                    "act_name": _("安装Spider集群中控实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=ctl_acts)

        shard_infos = self._assign_shards(apply_data["remote_group"], mysql_ports)
        repl_flows = []
        for info in shard_infos:
            repl_flows.append(
                build_repl_by_manual_input_sub_flow(
                    bk_cloud_id=apply_data["bk_cloud_id"],
                    root_id=self.root_id,
                    parent_global_data=apply_data,
                    master_ip=info.instance_tuple.master_ip,
                    slave_ip=info.instance_tuple.slave_ip,
                    master_port=info.instance_tuple.mysql_port,
                    slave_port=info.instance_tuple.mysql_port,
                    sub_flow_name="Shard{}".format(info.shard_key),
                )
            )
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=repl_flows)

        ctl_master = apply_data["spider_ip_list"][0]
        ctl_slaves = apply_data["spider_ip_list"][1:]
        sub_pipeline.add_act(
            act_name=_("构建spider中控集群同步"),
            act_component_code=SyncMasterComponent.code,
            kwargs=asdict(
                MysqlSyncMasterKwargs(
                    bk_biz_id=int(apply_data["bk_biz_id"]),
                    bk_cloud_id=int(apply_data["bk_cloud_id"]),
                    priv_role=PrivRole.TDBCTL.value,
                    master=Instance(host=ctl_master["ip"], port=apply_data["ctl_port"]),
                    slaves=[Instance(host=slave["ip"], port=apply_data["ctl_port"]) for slave in ctl_slaves],
                    is_gtid=True,
                    is_add_any=True,
                )
            ),
        )
        sub_pipeline.add_act(
            act_name=_("集群内部节点间授权"),
            act_component_code=AddSystemUserInClusterComponent.code,
            kwargs=asdict(
                AddSpiderSystemUserKwargs(ctl_master_ip=ctl_master["ip"], user=TDBCTL_USER, passwd=tdbctl_pass)
            ),
        )
        exec_act_kwargs.cluster = self._cluster_nodes(apply_data, shard_infos, tdbctl_pass)
        exec_act_kwargs.exec_ip = ctl_master
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_init_spider_routing_payload.__name__
        sub_pipeline.add_act(
            act_name=_("初始化集群节点间关系"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        sub_pipeline.add_act(
            act_name=_("添加集群域名"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                CreateDnsKwargs(
                    bk_cloud_id=apply_data["bk_cloud_id"],
                    add_domain_name=apply_data["immutable_domain"],
                    dns_op_exec_port=apply_data["spider_port"],
                    exec_ip=[ip_info["ip"] for ip_info in apply_data["spider_ip_list"]],
                )
            ),
        )
        sub_pipeline.add_act(
            act_name=_("更新DBMeta元信息"),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SpiderDBMeta.tendb_cluster_apply.__name__,
                    cluster={"shard_infos": shard_infos},
                    is_update_trans_data=True,
                )
            ),
        )
        instances = [
            "{}:{}".format(ip["ip"], port) for ip in apply_data["mysql_ip_list"] for port in apply_data["mysql_ports"]
        ]
        instances.extend(
            "{}:{}".format(ip["ip"], port)
            for ip in apply_data["spider_ip_list"]
            for port in apply_data["spider_ports"]
        )
        sub_pipeline.add_sub_pipeline(
            sub_flow=standardize_mysql_cluster_subflow(
                root_id=self.root_id,
                data=copy.deepcopy(apply_data),
                bk_cloud_id=int(apply_data["bk_cloud_id"]),
                bk_biz_id=apply_data["bk_biz_id"],
                instances=instances,
                with_actuator=False,
                with_bk_plugin=False,
                with_collect_sysinfo=True,
                with_instance_standardize=False,
            )
        )
        return sub_pipeline.build_sub_process(sub_name=_("上架TenDBCluster演练集群"))

    @staticmethod
    def _assign_shards(remote_group: List[Dict], mysql_ports: List[int]) -> List[ShardInfo]:
        shard_infos = []
        start_index = 0
        for remote in remote_group:
            for index, mysql_port in enumerate(mysql_ports):
                shard_infos.append(
                    ShardInfo(
                        shard_key=index + start_index,
                        instance_tuple=InstanceTuple(
                            master_ip=remote["master"]["ip"],
                            slave_ip=remote["slave"]["ip"],
                            mysql_port=mysql_port,
                        ),
                    )
                )
            start_index += len(mysql_ports)
        return shard_infos

    @staticmethod
    def _cluster_nodes(apply_data: Dict, shard_infos: List[ShardInfo], tdbctl_pass: str) -> dict:
        info = {
            "mysql_instance_tuples": [],
            "spider_instances": [],
            "ctl_instances": [],
            "tdbctl_user": TDBCTL_USER,
            "tdbctl_pass": tdbctl_pass,
        }
        for ip_info in apply_data["spider_ip_list"]:
            info["spider_instances"].append({"host": ip_info["ip"], "port": apply_data["spider_port"]})
            info["ctl_instances"].append({"host": ip_info["ip"], "port": apply_data["ctl_port"]})
        for shard in shard_infos:
            info["mysql_instance_tuples"].append(
                {
                    "host": shard.instance_tuple.master_ip,
                    "port": shard.instance_tuple.mysql_port,
                    "slave_host": shard.instance_tuple.slave_ip,
                    "shard_id": shard.shard_key,
                }
            )
        return info

    def _build_drill_subflows(self, city_data: Dict) -> List:
        """先 remote 再 spider，和旧演练 types 顺序一致。"""
        subs = []
        drill_ips = city_data["drill_ips"]
        for role in ("remote", "spider"):
            ip = drill_ips[role]
            drill = SubBuilder(root_id=self.root_id, data=copy.deepcopy(city_data))
            append_dbha_trigger_acts(drill, self.root_id, city_data, role, ip)
            subs.append(drill.build_sub_process(sub_name=_("触发DBHA {}").format(role)))
        return subs

    def _add_teardown(self, sub_pipeline: SubBuilder, city_data: Dict):
        """下架节点抄自 TenDBClusterDestroyFlow。不做禁用的连接检查。删域名、卸载实例、清元数据失败会停住。"""
        remote_ips = [ip["ip"] for ip in city_data["mysql_ip_list"]]
        spider_ips = [ip["ip"] for ip in city_data["spider_ip_list"]]
        spider_port = int(city_data["spider_port"])
        ctl_port = spider_port + 1000
        mysql_ports = [
            int(city_data["start_mysql_port"]) + index for index in range(int(city_data["remote_shard_num"]))
        ]
        domain = city_data["immutable_domain"]
        sub_pipeline.add_act(
            act_name=_("删除演练域名"),
            act_component_code=DrillClusterDnsDeleteComponent.code,
            kwargs={
                "bk_biz_id": city_data["bk_biz_id"],
                "bk_cloud_id": city_data["bk_cloud_id"],
                "immute_domain": domain,
            },
        )
        sub_pipeline.add_act(
            act_name=_("下发db-actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=city_data["bk_cloud_id"],
                    exec_ip=remote_ips + spider_ips,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
            error_ignorable=True,
        )
        exec_act_kwargs = ExecActuatorKwargs(bk_cloud_id=int(city_data["bk_cloud_id"]), cluster={})
        exec_act_kwargs.exec_ip = remote_ips + spider_ips
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
        sub_pipeline.add_act(
            act_name=_("清理机器级别配置"),
            act_component_code=SpiderRemoteClearMachineComponent.code,
            kwargs=asdict(exec_act_kwargs),
            error_ignorable=True,
        )

        spider_acts = []
        for spider_ip in spider_ips:
            exec_act_kwargs.exec_ip = spider_ip
            exec_act_kwargs.cluster = {"spider_port": spider_port}
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_spider_payload.__name__
            spider_acts.append(
                {
                    "act_name": _("卸载spider实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=spider_acts)

        ctl_acts = []
        for ctl_ip in spider_ips:
            exec_act_kwargs.exec_ip = ctl_ip
            exec_act_kwargs.cluster = {"spider_ctl_port": ctl_port}
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_spider_ctl_payload.__name__
            ctl_acts.append(
                {
                    "act_name": _("卸载中控实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=ctl_acts)

        mysql_acts = []
        for mysql_ip in remote_ips:
            for mysql_port in mysql_ports:
                exec_act_kwargs.exec_ip = mysql_ip
                exec_act_kwargs.cluster = {"backend_port": mysql_port}
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_mysql_payload.__name__
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
