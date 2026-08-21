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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import install_mysql_in_cluster_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import (
    mysql_restore_master_slave_sub_flow,
)
from backend.flow.engine.bamboo.scene.mysql.common.uninstall_instance import uninstall_instance_sub_flow
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import (
    ALLDEPARTS,
    DeployPeripheralToolsDepart,
    remove_departs,
)
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import remote_migrate_switch_sub_flow
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket import MySQLCheckSumTicketComponent
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket_result_get import (
    MySQLCheckSumTicketResultComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket_status import (
    MySQLCheckSumTicketProbeComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import (
    ClearMachineKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    MysqlCheckSumKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta
from backend.flow.utils.spider.tendb_cluster_info import get_master_slave_recover_info
from backend.ticket.builders.common.constants import MySQLBackupSource
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class TendbClusterMigrateRemoteFlow(object):
    """
    tendb cluster 后端remote节点主从成对迁移
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递参数
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        self.data = {}

        # 定义备份文件存放到目标机器目录位置
        self.backup_target_path = f"/data/dbbak/{self.root_id}"

    def migrate_master_slave_flow(self):
        """
        成对迁移集群主从节点。
        元数据信息修改顺序：
        1 mysql_migrate_cluster_add_instance
        2 mysql_migrate_cluster_add_tuple
        3 mysql_migrate_cluster_switch_storage
        """
        # 构建流程
        cluster_ids = []
        self.ticket_data["cluster_infos"] = {}
        for i in self.ticket_data["infos"]:
            cluster_ids.append(i["cluster_id"])
            if i["cluster_id"] not in self.ticket_data["cluster_infos"]:
                self.ticket_data["cluster_infos"][i["cluster_id"]] = []
            self.ticket_data["cluster_infos"][i["cluster_id"]].append(i)

        tendb_migrate_pipeline_all = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        # 按照传入的infos信息，循环拼接子流程
        tendb_migrate_pipeline_all_list = []
        for cluster_id, cluster_info in self.ticket_data["cluster_infos"].items():
            cluster_level_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.ticket_data))
            # 生成checksum信息
            cluster_class = Cluster.objects.get(id=cluster_id)
            checksum_pairs = []
            checksum_info = {
                "bk_biz_id": cluster_class.bk_biz_id,
                "ticket_type": TicketType.TENDBCLUSTER_CHECKSUM_CRON,
                "remark": _("spider主从成对迁移生成checksum单据"),
                # "ignore_duplication": True,
                "details": {
                    "data_repair": {"is_repair": True, "mode": "manual"},
                    # timing 执行checksum的时间在流程中生成
                    "is_sync_non_innodb": True,
                    "runtime_hour": 48,
                    "infos": [{"cluster_id": cluster_class.id, "checksum_scope": "partial", "backup_infos": []}],
                },
            }
            # 机器安装子流程列表
            install_sub_pipeline_list = []
            # 实例同步子流程列表
            sync_data_sub_pipeline_list = []
            # 实例切换子流程列表
            # switch_sub_pipeline_list = []
            # 机器卸载子流程列表
            uninstall_svr_sub_pipeline_list = []
            # 新实例列表,供安装周边&屏蔽告警使用
            new_instances = []
            # 构建切换分片信息
            switch_shard_list = []
            # 构建切换后修改元数据信息
            cluster_info_meta = {"cluster_id": cluster_class.id, "shards": {}}
            for info in cluster_info:
                # 获取集群所有信息。计算端口,构建流程数据
                self.data = copy.deepcopy(info)
                self.data["need_checksum"] = self.ticket_data.get("need_checksum", False)
                self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
                self.data["root_id"] = self.root_id
                self.data["uid"] = self.ticket_data["uid"]
                self.data["created_by"] = self.ticket_data["created_by"]
                self.data["ticket_type"] = self.ticket_data["ticket_type"]
                self.data["bk_biz_id"] = cluster_class.bk_biz_id
                self.data["db_module_id"] = cluster_class.db_module_id
                self.data["cluster_type"] = cluster_class.cluster_type
                self.data["force"] = True
                self.data["charset"], self.data["db_version"] = get_version_and_charset(
                    bk_biz_id=cluster_class.bk_biz_id,
                    db_module_id=cluster_class.db_module_id,
                    cluster_type=cluster_class.cluster_type,
                )

                cluster_info = get_master_slave_recover_info(
                    cluster_class.id, self.data["old_master_ip"], self.data["old_slave_ip"]
                )
                cluster_info["charset"] = self.data["charset"]
                cluster_info["db_version"] = self.data["db_version"]
                cluster_info["ports"] = []
                # 构建切换后写入元数据信息
                cluster_info_meta["shards"].update(cluster_info["my_shards"])
                for shard_id, shard in cluster_info["my_shards"].items():
                    master = {
                        "ip": self.data["new_master_ip"],
                        "port": shard["master"]["port"],
                        "bk_cloud_id": self.data["bk_cloud_id"],
                        "instance": "{}{}{}".format(
                            self.data["new_master_ip"], IP_PORT_DIVIDER, shard["master"]["port"]
                        ),
                    }

                    slave = {
                        "ip": self.data["new_slave_ip"],
                        "port": shard["slave"]["port"],
                        "bk_cloud_id": self.data["bk_cloud_id"],
                        "instance": "{}{}{}".format(
                            self.data["new_slave_ip"], IP_PORT_DIVIDER, shard["slave"]["port"]
                        ),
                    }

                    cluster_info["my_shards"][shard_id]["new_slave"] = slave
                    cluster_info["my_shards"][shard_id]["new_master"] = master
                    cluster_info["ports"].append(shard["master"]["port"])

                # 构造安装remoteDB实例&恢复环境子流程 机器级别
                db_config = get_instance_config(
                    cluster_class.bk_cloud_id, self.data["old_master_ip"], cluster_info["ports"]
                )
                install_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

                install_sub_pipeline.add_sub_pipeline(
                    sub_flow=install_mysql_in_cluster_sub_flow(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        cluster=cluster_class,
                        new_mysql_list=[self.data["new_master_ip"], self.data["new_slave_ip"]],
                        install_ports=cluster_info["ports"],
                        bk_host_ids=[
                            self.data["bk_new_master"]["bk_host_id"],
                            self.data["bk_new_slave"]["bk_host_id"],
                        ],
                        db_config=db_config,
                    )
                )

                cluster = {
                    "new_master_ip": self.data["new_master_ip"],
                    "new_slave_ip": self.data["new_slave_ip"],
                    "cluster_id": cluster_class.id,
                    "bk_cloud_id": cluster_class.bk_cloud_id,
                    "bk_biz_id": cluster_class.bk_biz_id,
                    "ports": cluster_info["ports"],
                    "version": cluster_class.major_version,
                }
                install_sub_pipeline.add_act(
                    act_name=_("写入初始化实例的db_meta元信息"),
                    act_component_code=SpiderDBMetaComponent.code,
                    kwargs=asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=SpiderDBMeta.remotedb_migrate_add_install_nodes.__name__,
                            cluster=copy.deepcopy(cluster),
                            is_update_trans_data=False,
                        )
                    ),
                )

                install_sub_pipeline.add_act(
                    act_name=_("安装backup-client工具"),
                    act_component_code=DownloadBackupClientComponent.code,
                    kwargs=asdict(
                        DownloadBackupClientKwargs(
                            bk_cloud_id=cluster_class.bk_cloud_id,
                            bk_biz_id=int(cluster_class.bk_biz_id),
                            ip_list=[cluster["new_master_ip"], cluster["new_slave_ip"]],
                        )
                    ),
                )

                exec_act_kwargs = ExecActuatorKwargs(
                    cluster=cluster,
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    cluster_type=cluster_class.cluster_type,
                    get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
                )
                exec_act_kwargs.exec_ip = [cluster["new_master_ip"], cluster["new_slave_ip"]]
                install_sub_pipeline.add_act(
                    act_name=_("安装临时备份程序"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )
                install_sub_pipeline_list.append(
                    install_sub_pipeline.build_sub_process(
                        sub_name=_("安装实例 {} {}".format(self.data["new_master_ip"], self.data["new_slave_ip"]))
                    )
                )

                # 构造老实例同步数据到新实例子流程  切换子流程  实例级别
                for shard_id, node in cluster_info["my_shards"].items():
                    # 构造checksum参数
                    checksum_info["details"]["infos"][0]["backup_infos"].append(
                        {
                            "master": node["master"]["instance"],
                            "slave": node["new_master"]["instance"],
                            "db_patterns": ["*"],
                            "ignore_dbs": [],
                            "table_patterns": ["*"],
                            "ignore_tables": [],
                        }
                    )
                    checksum_pairs.append(
                        {
                            "master": node["master"]["instance"],
                            "slave": node["new_master"]["instance"],
                        }
                    )
                    # 构建切切换流程的分片信息 实例级别
                    shard_cluster = {
                        "old_master": node["master"]["instance"],
                        "old_slave": node["slave"]["instance"],
                        "new_master": node["new_master"]["instance"],
                        "new_slave": node["new_slave"]["instance"],
                    }
                    switch_shard_list.append(shard_cluster)

                    # 构造实例级数据同步信息
                    ins_cluster = copy.deepcopy(cluster_info["cluster"])
                    ins_cluster["charset"] = cluster_info["charset"]
                    ins_cluster["new_master_ip"] = node["new_master"]["ip"]
                    ins_cluster["new_slave_ip"] = node["new_slave"]["ip"]
                    ins_cluster["new_master_port"] = node["new_master"]["port"]
                    ins_cluster["new_slave_port"] = node["new_slave"]["port"]
                    ins_cluster["master_ip"] = node["master"]["ip"]
                    ins_cluster["slave_ip"] = node["slave"]["ip"]
                    ins_cluster["master_port"] = node["master"]["port"]
                    ins_cluster["slave_port"] = node["slave"]["port"]
                    ins_cluster["file_target_path"] = f"{self.backup_target_path}/{node['new_master']['port']}"
                    ins_cluster["shard_id"] = shard_id
                    ins_cluster["change_master_force"] = False
                    ins_cluster["backup_source"] = self.ticket_data["backup_source"]
                    new_instances.extend(
                        [
                            "{}:{}".format(ins_cluster["new_slave_ip"], ins_cluster["new_slave_port"]),
                            "{}:{}".format(ins_cluster["new_master_ip"], ins_cluster["new_master_port"]),
                        ]
                    )
                    sync_data_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

                    filter_ips = None
                    if self.ticket_data["backup_source"] == MySQLBackupSource.LOCAL.value:
                        filter_ips = [node["master"]["ip"], node["slave"]["ip"]]
                    sync_data_sub_pipeline.add_sub_pipeline(
                        sub_flow=mysql_restore_master_slave_sub_flow(
                            root_id=self.root_id,
                            ticket_data=copy.deepcopy(self.data),
                            cluster=ins_cluster,
                            cluster_model=cluster_class,
                            filter_ips=filter_ips,
                        )
                    )

                    sync_data_sub_pipeline.add_act(
                        act_name=_("恢复完毕,写入数据节点的主从关系"),
                        act_component_code=SpiderDBMetaComponent.code,
                        kwargs=asdict(
                            DBMetaOPKwargs(
                                db_meta_class_func=SpiderDBMeta.remotedb_migrate_add_storage_tuple.__name__,
                                cluster=ins_cluster,
                                is_update_trans_data=True,
                            )
                        ),
                    )
                    sync_data_sub_pipeline_list.append(
                        sync_data_sub_pipeline.build_sub_process(
                            sub_name=_(
                                "恢复分片{} {} -> {} {} -> {}".format(
                                    shard_id, node["master"], node["new_master"], node["slave"], node["new_slave"]
                                )
                            )
                        )
                    )

                #  构造卸载实例子流程  机器级别
                for ip in [self.data["old_master_ip"], self.data["old_slave_ip"]]:
                    uninstall_svr_sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                    uninstall_svr_sub_pipeline.add_act(
                        act_name=_("下发db-actor到节点{}".format(ip)),
                        act_component_code=TransFileComponent.code,
                        kwargs=asdict(
                            DownloadMediaKwargs(
                                bk_cloud_id=cluster_class.bk_cloud_id,
                                exec_ip=[ip],
                                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                            )
                        ),
                    )
                    ins_cluster = {"uninstall_ip": ip, "cluster_id": cluster_class.id}
                    uninstall_svr_sub_pipeline.add_act(
                        act_name=_("整机卸载前删除元数据"),
                        act_component_code=SpiderDBMetaComponent.code,
                        kwargs=asdict(
                            DBMetaOPKwargs(
                                db_meta_class_func=SpiderDBMeta.remotedb_migrate_remove_storage.__name__,
                                cluster=ins_cluster,
                                is_update_trans_data=True,
                            )
                        ),
                    )
                    uninstall_svr_sub_pipeline.add_act(
                        act_name=_("清理机器配置"),
                        act_component_code=MySQLClearMachineComponent.code,
                        kwargs=asdict(
                            ClearMachineKwargs(
                                exec_ip=ip,
                                bk_cloud_id=cluster_class.bk_cloud_id,
                            )
                        ),
                    )
                    uninstall_svr_sub_pipeline.add_sub_pipeline(
                        sub_flow=uninstall_instance_sub_flow(
                            root_id=self.root_id, ticket_data=copy.deepcopy(self.data), ip=ip
                        )
                    )
                    uninstall_svr_sub_pipeline_list.append(
                        uninstall_svr_sub_pipeline.build_sub_process(sub_name=_("卸载remote节点{}").format(ip))
                    )
            if len(sync_data_sub_pipeline_list) == 0:
                raise Exception(_("同步子流程列表为空,请检查备份信息是否缺失"))
            if (
                len(install_sub_pipeline_list) == 0
                or len(uninstall_svr_sub_pipeline_list) == 0
                or len(new_instances) == 0
                or len(switch_shard_list) == 0
            ):
                raise Exception(_("安装/卸载/新实例/切换实例为空,请检查参数"))
            # === 主流程 串联各个子流程 ===
            # 安装remote节点
            cluster_level_pipeline.add_parallel_sub_pipeline(sub_flow_list=install_sub_pipeline_list)
            # 屏蔽新节点告警
            cluster_level_pipeline.add_act(
                act_name=_("屏蔽告警24小时"),
                act_component_code=AddAlarmShieldComponent.code,
                kwargs={
                    "duration_seconds": 24 * 3600,
                    "description": cluster_class.immute_domain,
                    "dimensions": [
                        {
                            "name": "instance_host",
                            "values": list(set([ins.split(IP_PORT_DIVIDER)[0] for ins in new_instances])),
                        }
                    ],
                },
            )
            # 新实例同步数据
            cluster_level_pipeline.add_parallel_sub_pipeline(sub_flow_list=sync_data_sub_pipeline_list)
            if self.data["need_checksum"]:
                cluster_level_pipeline.add_act(
                    act_name=MySQLCheckSumTicketComponent.node_name,
                    act_component_code=MySQLCheckSumTicketComponent.code,
                    kwargs=asdict(
                        MysqlCheckSumKwargs(
                            uid=self.data["uid"],
                            bk_biz_id=cluster_class.bk_biz_id,
                            created_by=self.data["created_by"],
                            checksum_info=checksum_info,
                        )
                    ),
                )
                cluster_level_pipeline.add_act(
                    act_name=MySQLCheckSumTicketProbeComponent.node_name,
                    act_component_code=MySQLCheckSumTicketProbeComponent.code,
                    kwargs={},
                )
                cluster_level_pipeline.add_act(
                    act_name=MySQLCheckSumTicketResultComponent.node_name,
                    act_component_code=MySQLCheckSumTicketResultComponent.code,
                    kwargs={
                        "bk_cloud_id": cluster_class.bk_cloud_id,
                        "checksum_pairs": checksum_pairs,
                        "cluster_id": cluster_class.id,
                    },
                )
            # 同步完安装周边
            cluster_level_pipeline.add_sub_pipeline(
                sub_flow=standardize_mysql_cluster_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    bk_biz_id=self.data["bk_biz_id"],
                    instances=new_instances,
                    departs=remove_departs(ALLDEPARTS, DeployPeripheralToolsDepart.MySQLDBBackup),
                    with_actuator=False,
                    with_bk_plugin=False,
                    with_collect_sysinfo=False,
                    with_instance_standardize=False,
                    with_cc_standardize=False,
                    with_probe=False,
                )
            )
            # todo 添加checksum单据状态检查 、添加通过后添加checksum结果的查询
            # 人工确定切换
            cluster_level_pipeline.add_act(
                act_name=_("人工确认切换 {}".format(cluster_class.name)), act_component_code=PauseComponent.code, kwargs={}
            )
            # 切换到新实例
            cluster_level_pipeline.add_sub_pipeline(
                sub_flow=remote_migrate_switch_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    cluster=cluster_class,
                    migrate_tuples=switch_shard_list,
                    created_by=self.data["created_by"],
                )
            )
            cluster_level_pipeline.add_act(
                act_name=_("切换完毕后修改元数据指向"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.tendb_remotedb_rebalance_switch.__name__,
                        cluster=cluster_info_meta,
                        is_update_trans_data=True,
                    )
                ),
            )
            # 切换后重安装周边
            cluster_level_pipeline.add_sub_pipeline(
                sub_flow=standardize_mysql_cluster_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    bk_biz_id=self.data["bk_biz_id"],
                    instances=new_instances,
                    with_actuator=False,
                    with_collect_sysinfo=False,
                    with_instance_standardize=False,
                    with_bk_plugin=False,
                    with_backup_client=False,
                )
            )
            # 解除告警屏蔽
            cluster_level_pipeline.add_act(
                act_name=DisableAlarmShieldComponent.node_name,
                act_component_code=DisableAlarmShieldComponent.code,
                kwargs={},
            )
            # 人工确定卸载实例
            cluster_level_pipeline.add_act(
                act_name=_("人工确认卸载实例 {}".format(cluster_class.name)), act_component_code=PauseComponent.code, kwargs={}
            )
            # 卸载实例
            cluster_level_pipeline.add_parallel_sub_pipeline(sub_flow_list=uninstall_svr_sub_pipeline_list)
            # 集群维度构建子流程
            tendb_migrate_pipeline_all_list.append(
                cluster_level_pipeline.build_sub_process(_("集群迁移 {} {}").format(cluster_class.id, cluster_class.name))
            )
        # 主流程并发执行所有集群迁移子流程
        if len(tendb_migrate_pipeline_all_list) == 0:
            raise Exception(_("没有生成集群迁移流程"))
        tendb_migrate_pipeline_all.add_parallel_sub_pipeline(tendb_migrate_pipeline_all_list)
        # 执行主流程
        # tendb_migrate_pipeline_all.run_pipeline(
        #     init_trans_data_class=ClusterInfoContext(),
        #     is_drop_random_user=True,
        # )
        # 启动接入单据值守监听
        tendb_migrate_pipeline_all.run_pipeline_with_sidecar(
            init_trans_data_class=ClusterInfoContext(),
            is_drop_random_user=True,
            check_ai_monitor_cluster_list=list(set(cluster_ids)),
        )
