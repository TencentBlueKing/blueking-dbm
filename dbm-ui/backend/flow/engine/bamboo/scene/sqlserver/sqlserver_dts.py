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
from pathlib import PureWindowsPath

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_meta.models.sqlserver_dts import DtsStatus, SqlserverDtsInfo
from backend.flow.consts import (
    DBM_SQLSERVER_JOB_LONG_TIMEOUT,
    SqlserverBackupFileTagEnum,
    SqlserverBackupJobExecMode,
    SqlserverBackupMode,
    SqlserverDtsMode,
    SqlserverRestoreDBStatus,
    SqlserverRestoreMode,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.plugins.components.collections.sqlserver.backup_path_file_trans import (
    SqlserverTransBackupFileFor2P2Component,
)
from backend.flow.plugins.components.collections.sqlserver.create_random_job_user import SqlserverAddJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.drop_random_job_user import SqlserverDropJobUserComponent
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.exec_sqlserver_backup_job import (
    ExecSqlserverBackupJobComponent,
)
from backend.flow.plugins.components.collections.sqlserver.restore_for_dts import RestoreForDtsComponent
from backend.flow.plugins.components.collections.sqlserver.sqlserver_db_meta import SqlserverDBMetaComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    CreateRandomJobUserKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    DropRandomJobUserKwargs,
    ExecActuatorKwargs,
    ExecBackupJobsKwargs,
    P2PFileForWindowKwargs,
    RestoreForDtsKwargs,
    SqlserverBackupIDContext,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import create_sqlserver_login_sid, get_backup_path
from backend.flow.utils.sqlserver.sqlserver_db_meta import SqlserverDBMeta
from backend.flow.utils.sqlserver.sqlserver_host import Host


class SqlserverDTSFlow(BaseFlow):
    """
    构建sqlserver数据迁移服务流程的抽象类
    兼容跨云区域的场景支持
    """

    def __calc_target_backup_path(self, cluster_id: int, port: int, tag: str) -> str:
        """
        内部函数，计算当前适用的备份文件传输点
        """
        # 获取源集群的备份路径
        cluster_backup_path = get_backup_path(cluster_id)
        if cluster_backup_path == "":
            # 如果没有配置，则用默认路径
            return str(PureWindowsPath("d:/") / "dbbak" / f"dts_{tag}_{self.root_id}_{port}")
        else:
            return str(PureWindowsPath(cluster_backup_path) / f"dts_{tag}_{self.root_id}_{port}")

    def full_dts_flow(self):
        """
        定义全量数据传输的流程：
        触发场景
        1：用户提交全量数据迁移的单据
        2：用户提交增量数据迁移的单据，第一次触发需要做一次全量数据迁移
        执行逻辑
        1：禁用backup job
        1：给目标集群的master和源集群master下发执行器
        2：在源集群master执行全量备份
        2：在源集群master执行日志备份
        3：源和目标不在同一台机器上，则利用job传输备份文件（可选）
        4：恢复全量备份文件
        4：恢复日志备份文件
        5：重新启动backup job（可选）
        6：更改迁移记录状态
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 计算源集群和目标集群的master
            cluster = Cluster.objects.get(id=info["src_cluster"])
            target_cluster = Cluster.objects.get(id=info["dst_cluster"])

            # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
            master_instance = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )
            target_master_instance = target_cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )

            # 获取源集群的备份路径
            cluster_backup_path = get_backup_path(cluster.id)
            if cluster_backup_path == "":
                # 如果没有配置，则用默认路径
                target_backup_path = backup_path = str(
                    PureWindowsPath("d:/") / "dbbak" / f"dts_full_{self.root_id}_{master_instance.port}"
                )
            else:
                target_backup_path = backup_path = str(
                    PureWindowsPath(cluster_backup_path) / f"dts_full_{self.root_id}_{master_instance.port}"
                )

            # 拼接子流程，子流程并发执行
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context["dts_infos"] = sub_flow_context.pop("rename_infos")
            sub_flow_context["target_backup_dir"] = backup_path
            sub_flow_context["job_id"] = f"dts_full_{self.root_id}_{master_instance.port}"
            sub_flow_context["backup_dbs"] = [i["db_name"] for i in info["rename_infos"]]
            sub_flow_context["is_set_full_model"] = False

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 创建随机账号
            sub_pipeline.add_act(
                act_name=_("create temp job account"),
                act_component_code=SqlserverAddJobUserComponent.code,
                kwargs=asdict(
                    CreateRandomJobUserKwargs(
                        cluster_ids=[cluster.id, target_cluster.id],
                        sid=create_sqlserver_login_sid(),
                    ),
                ),
            )

            # 先禁用原集群的master例行备份逻辑
            sub_pipeline.add_act(
                act_name=_("禁用源master[{}]的backup jobs".format(master_instance.ip_port)),
                act_component_code=ExecSqlserverBackupJobComponent.code,
                kwargs=asdict(
                    ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.DISABLE),
                ),
            )

            # 给目标集群的master和源集群master下发执行器
            sub_pipeline.add_act(
                act_name=_("下发执行器"),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=[
                            Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                            Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id),
                        ],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )

            # 在源集群master执行备份
            sub_pipeline.add_act(
                act_name=_("在源集群[{}]执行数据库备份".format(master_instance.ip_port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                        custom_params={
                            "port": master_instance.port,
                            "file_tag": SqlserverBackupFileTagEnum.DBFILE1M.value,
                            "backup_type": SqlserverBackupMode.FULL_BACKUP.value,
                        },
                    )
                ),
                write_payload_var=SqlserverBackupIDContext.full_backup_id_var_name(),
            )

            # 执行数据库日志备份
            sub_pipeline.add_act(
                act_name=_("在源集群[{}]执行数据库日志备份".format(master_instance.ip_port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                        custom_params={
                            "port": master_instance.port,
                            "file_tag": SqlserverBackupFileTagEnum.INCREMENT_BACKUP.value,
                            "backup_type": SqlserverBackupMode.LOG_BACKUP.value,
                        },
                    )
                ),
                write_payload_var=SqlserverBackupIDContext.log_backup_id_var_name(),
            )
            if master_instance.machine.ip != target_master_instance.machine.ip:
                # 源和目标不在同一台机器上，则利用job传输备份文件
                # 这里计算出目标集群的恢复目录
                # 获取源集群的备份路径
                target_cluster_backup_path = get_backup_path(target_cluster.id)
                if target_cluster_backup_path == "":
                    # 如果没有配置，则用默认路径
                    target_backup_path = str(
                        PureWindowsPath("d:/") / "dbbak" / f"dts_full_{self.root_id}_{master_instance.port}"
                    )
                else:
                    target_backup_path = str(
                        PureWindowsPath(target_cluster_backup_path) / f"dts_full_{self.root_id}_{master_instance.port}"
                    )
                sub_pipeline.add_act(
                    act_name=_("传送文件到目标机器[{}]".format(target_master_instance.machine.ip)),
                    act_component_code=SqlserverTransBackupFileFor2P2Component.code,
                    kwargs=asdict(
                        P2PFileForWindowKwargs(
                            source_hosts=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                            target_hosts=[
                                Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)
                            ],
                            file_target_path=target_backup_path,
                            cluster_id=cluster.id,
                        ),
                    ),
                )

            # 恢复全量备份文件
            sub_pipeline.add_act(
                act_name=_("恢复全量备份数据[{}]".format(target_master_instance.ip_port)),
                act_component_code=RestoreForDtsComponent.code,
                kwargs=asdict(
                    RestoreForDtsKwargs(
                        cluster_id=cluster.id,
                        job_id=sub_flow_context["job_id"],
                        restore_infos=sub_flow_context["dts_infos"],
                        restore_mode=SqlserverRestoreMode.FULL.value,
                        restore_db_status=SqlserverRestoreDBStatus.NORECOVERY.value,
                        restore_path=target_backup_path,
                        exec_ips=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                        port=target_master_instance.port,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                    )
                ),
            )

            # 恢复日志备份文件
            if self.data["dts_mode"] == SqlserverDtsMode.INCR.value:
                restore_db_status = SqlserverRestoreDBStatus.NORECOVERY.value
            else:
                restore_db_status = SqlserverRestoreDBStatus.RECOVERY.value

            sub_pipeline.add_act(
                act_name=_("恢复增量备份数据[{}]".format(target_master_instance.ip_port)),
                act_component_code=RestoreForDtsComponent.code,
                kwargs=asdict(
                    RestoreForDtsKwargs(
                        cluster_id=cluster.id,
                        job_id=sub_flow_context["job_id"],
                        restore_infos=sub_flow_context["dts_infos"],
                        restore_mode=SqlserverRestoreMode.LOG.value,
                        restore_db_status=restore_db_status,
                        restore_path=target_backup_path,
                        exec_ips=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                        port=target_master_instance.port,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                    )
                ),
            )

            if self.data["dts_mode"] == SqlserverDtsMode.FULL.value:
                # 重新启动源master的例行备份逻辑
                sub_pipeline.add_act(
                    act_name=_("启动源master[{}]的backup jobs".format(master_instance.ip_port)),
                    act_component_code=ExecSqlserverBackupJobComponent.code,
                    kwargs=asdict(
                        ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.ENABLE),
                    ),
                )
            # 更改迁移记录状态
            sub_pipeline.add_act(
                act_name=_("更新任务状态"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.update_dts_status.__name__,
                    )
                ),
            )

            # 删除随机账号
            sub_pipeline.add_act(
                act_name=_("remove temp job account"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id, target_cluster.id])),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("[{}]->[{}]全量数据迁移流程".format(cluster.name, target_cluster.name))
                )
            )
            # 更新root_id在迁移表上，并标记online状态
            SqlserverDtsInfo.objects.filter(id=info["dts_id"]).update(
                root_id=self.root_id, status=DtsStatus.FullOnline
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline(init_trans_data_class=SqlserverBackupIDContext())

    def incr_dts_flow(self):
        """
        定义增量数据传输的流程：
        触发场景
        1：定期触发（暂时未实现）
        2：用户提交中断同步需求，执行最后一次需求
        执行逻辑
        1：给目标集群的master和源集群master下发执行器
        2：在源集群master执行日志备份
        3：源和目标不在同一台机器上，则利用job传输备份文件（可选）
        4：恢复日志备份文件
        5：重新启动源master的例行备份逻辑（可选）
        6：更改迁移记录状态
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 计算源集群和目标集群的master
            cluster = Cluster.objects.get(id=info["src_cluster"])
            target_cluster = Cluster.objects.get(id=info["dst_cluster"])

            # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
            master_instance = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )
            target_master_instance = target_cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )
            # 获取集群的备份路径
            cluster_backup_path = get_backup_path(cluster.id)
            if cluster_backup_path == "":
                # 如果没有配置，则用默认路径
                target_backup_path = backup_path = str(
                    PureWindowsPath("d:/") / "dbbak" / f"dts_incr_{self.root_id}_{master_instance.port}"
                )
            else:
                target_backup_path = backup_path = str(
                    PureWindowsPath(cluster_backup_path) / f"dts_incr_{self.root_id}_{master_instance.port}"
                )

            # 拼接子流程，子流程并发执行
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context["dts_infos"] = sub_flow_context.pop("rename_infos")
            sub_flow_context["target_backup_dir"] = backup_path
            sub_flow_context["job_id"] = f"dts_incr_{self.root_id}_{master_instance.port}"
            sub_flow_context["backup_dbs"] = [i["db_name"] for i in info["rename_infos"]]

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 创建随机账号
            sub_pipeline.add_act(
                act_name=_("create temp job account"),
                act_component_code=SqlserverAddJobUserComponent.code,
                kwargs=asdict(
                    CreateRandomJobUserKwargs(
                        cluster_ids=[cluster.id, target_cluster.id],
                        sid=create_sqlserver_login_sid(),
                    ),
                ),
            )

            # 给目标集群的master和源集群master下发执行器
            sub_pipeline.add_act(
                act_name=_("下发执行器"),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=[
                            Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id),
                            Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id),
                        ],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )

            # 执行数据库日志备份
            sub_pipeline.add_act(
                act_name=_("在源集群[{}]执行数据库日志备份".format(master_instance.ip_port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                        job_timeout=3 * 3600,
                        custom_params={
                            "port": master_instance.port,
                            "file_tag": SqlserverBackupFileTagEnum.INCREMENT_BACKUP.value,
                            "backup_type": SqlserverBackupMode.LOG_BACKUP.value,
                        },
                    )
                ),
                write_payload_var=SqlserverBackupIDContext.log_backup_id_var_name(),
            )
            if master_instance.machine.ip != target_master_instance.machine.ip:
                # 源和目标不在同一台机器上，则利用job传输备份文件
                # 这里计算出目标集群的恢复目录
                # 获取源集群的备份路径
                target_cluster_backup_path = get_backup_path(target_cluster.id)
                if target_cluster_backup_path == "":
                    # 如果没有配置，则用默认路径
                    target_backup_path = str(
                        PureWindowsPath("d:/") / "dbbak" / f"dts_incr_{self.root_id}_{master_instance.port}"
                    )
                else:
                    target_backup_path = str(
                        PureWindowsPath(target_cluster_backup_path) / f"dts_incr_{self.root_id}_{master_instance.port}"
                    )

                sub_pipeline.add_act(
                    act_name=_("传送文件到目标机器[{}]".format(target_master_instance.machine.ip)),
                    act_component_code=SqlserverTransBackupFileFor2P2Component.code,
                    kwargs=asdict(
                        P2PFileForWindowKwargs(
                            source_hosts=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                            target_hosts=[
                                Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)
                            ],
                            file_target_path=target_backup_path,
                            cluster_id=cluster.id,
                            is_trans_full_backup=False,
                        ),
                    ),
                )

            # 恢复日志备份文件
            if self.data["is_last"]:
                restore_db_status = SqlserverRestoreDBStatus.RECOVERY.value
            else:
                restore_db_status = SqlserverRestoreDBStatus.NORECOVERY.value

            sub_pipeline.add_act(
                act_name=_("恢复增量备份数据[{}]".format(target_master_instance.ip_port)),
                act_component_code=RestoreForDtsComponent.code,
                kwargs=asdict(
                    RestoreForDtsKwargs(
                        cluster_id=cluster.id,
                        job_id=sub_flow_context["job_id"],
                        restore_infos=sub_flow_context["dts_infos"],
                        restore_mode=SqlserverRestoreMode.LOG.value,
                        restore_db_status=restore_db_status,
                        restore_path=target_backup_path,
                        exec_ips=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                        port=target_master_instance.port,
                        job_timeout=3 * 3600,
                    )
                ),
            )

            if self.data["is_last"]:
                # 重新启动源master的例行备份逻辑
                sub_pipeline.add_act(
                    act_name=_("启动源master[{}]的backup jobs".format(master_instance.ip_port)),
                    act_component_code=ExecSqlserverBackupJobComponent.code,
                    kwargs=asdict(
                        ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.ENABLE),
                    ),
                )
            # 更改迁移记录状态
            sub_pipeline.add_act(
                act_name=_("更新任务状态"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.update_dts_status.__name__,
                    )
                ),
            )

            # 删除随机账号
            sub_pipeline.add_act(
                act_name=_("remove temp job account"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id, target_cluster.id])),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("[{}]->[{}]增量数据迁移流程".format(cluster.name, target_cluster.name))
                )
            )

            # 更新root_id在迁移表上，并标记online状态
            SqlserverDtsInfo.objects.filter(id=info["dts_id"]).update(
                root_id=self.root_id, status=DtsStatus.IncrOnline
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline(init_trans_data_class=SqlserverBackupIDContext())

    def termination_dts_flow(self):
        """
        定义强制终止的流程：
        """
        termination_dts = Builder(root_id=self.root_id, data=self.data)

        cluster_ids = self.data["cluster_ids"]
        for cluster_id in cluster_ids:
            termination_dts.add_act(
                act_name=_("启动backup jobs cluster:{}".format(cluster_id)),
                act_component_code=ExecSqlserverBackupJobComponent.code,
                kwargs=asdict(
                    ExecBackupJobsKwargs(cluster_id=cluster_id, exec_mode=SqlserverBackupJobExecMode.ENABLE),
                ),
            )
        termination_dts.run_pipeline()

    def full_dts_flow_v2(self):
        """
        定义全量数据传输的流程, v2版本，支持一对一、多对一、一对多模式：
        触发场景
        1：用户提交全量数据迁移的单据
        2：用户提交增量数据迁移的单据，第一次触发需要做一次全量数据迁移
        执行逻辑
        1：禁用backup job
        1：给目标集群的master和源集群master下发执行器
        2：在源集群master执行全量备份
        2：在源集群master执行日志备份
        3：源和目标不在同一台机器上，则利用job传输备份文件（可选）
        4：恢复全量备份文件
        4：恢复日志备份文件
        5：重新启动backup job（可选）
        6：更改迁移记录状态
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 计算源集群和目标集群的master
            info["dst_cluster_list"] = [info["dst_cluster"]]
            cluster = Cluster.objects.get(id=info["src_cluster"])
            target_clusters = Cluster.objects.filter(id__in=info["dst_cluster_list"])

            # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
            master_instance = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )

            # 获取源集群的备份路径
            backup_path = self.__calc_target_backup_path(cluster.id, master_instance.port, "full")

            # 拼接子流程，子流程并发执行
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context["dts_infos"] = sub_flow_context.pop("rename_infos")
            sub_flow_context["target_backup_dir"] = backup_path
            sub_flow_context["job_id"] = f"dts_full_{self.root_id}_{master_instance.port}"
            sub_flow_context["backup_dbs"] = [i["db_name"] for i in info["rename_infos"]]
            sub_flow_context["is_set_full_model"] = False

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 创建随机账号
            sub_pipeline.add_act(
                act_name=_("create temp job account"),
                act_component_code=SqlserverAddJobUserComponent.code,
                kwargs=asdict(
                    CreateRandomJobUserKwargs(
                        cluster_ids=[cluster.id] + [c.id for c in target_clusters],
                        sid=create_sqlserver_login_sid(),
                    ),
                ),
            )

            # 先禁用原集群的master例行备份逻辑
            sub_pipeline.add_act(
                act_name=_("禁用源master[{}]的backup jobs".format(master_instance.ip_port)),
                act_component_code=ExecSqlserverBackupJobComponent.code,
                kwargs=asdict(
                    ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.DISABLE),
                ),
            )

            # 给目标集群的master和源集群master下发执行器
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

            # 在源集群master执行备份
            sub_pipeline.add_act(
                act_name=_("在源集群[{}]执行数据库备份".format(master_instance.ip_port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                        custom_params={
                            "port": master_instance.port,
                            "file_tag": SqlserverBackupFileTagEnum.DBFILE1M.value,
                            "backup_type": SqlserverBackupMode.FULL_BACKUP.value,
                        },
                    )
                ),
                write_payload_var=SqlserverBackupIDContext.full_backup_id_var_name(),
            )

            # 执行数据库日志备份
            sub_pipeline.add_act(
                act_name=_("在源集群[{}]执行数据库日志备份".format(master_instance.ip_port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                        job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                        custom_params={
                            "port": master_instance.port,
                            "file_tag": SqlserverBackupFileTagEnum.INCREMENT_BACKUP.value,
                            "backup_type": SqlserverBackupMode.LOG_BACKUP.value,
                        },
                    )
                ),
                write_payload_var=SqlserverBackupIDContext.log_backup_id_var_name(),
            )
            target_sub_pipelines = []
            for target_cluster in target_clusters:
                target_sub_pipelines.append(
                    self.__full_restore_sub_flow(
                        sub_flow_context=sub_flow_context,
                        source_cluster=cluster,
                        source_instance=master_instance,
                        target_cluster=target_cluster,
                    )
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=target_sub_pipelines)

            if self.data["dts_mode"] == SqlserverDtsMode.FULL.value:
                # 重新启动源master的例行备份逻辑
                sub_pipeline.add_act(
                    act_name=_("启动源master[{}]的backup jobs".format(master_instance.ip_port)),
                    act_component_code=ExecSqlserverBackupJobComponent.code,
                    kwargs=asdict(
                        ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.ENABLE),
                    ),
                )
            # 更改迁移记录状态
            sub_pipeline.add_act(
                act_name=_("更新任务状态"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.update_dts_status.__name__,
                    )
                ),
            )

            # 删除随机账号
            sub_pipeline.add_act(
                act_name=_("remove temp job account"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id] + [c.id for c in target_clusters])),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]全量数据迁移流程".format(cluster.name))))
            # 更新root_id在迁移表上，并标记online状态
            SqlserverDtsInfo.objects.filter(id=info["dts_id"]).update(
                root_id=self.root_id, status=DtsStatus.FullOnline
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline(init_trans_data_class=SqlserverBackupIDContext())

    def incr_dts_flow_v2(self):
        """
        定义增量数据传输的流程：
        触发场景
        1：定期触发（暂时未实现）
        2：用户提交中断同步需求，执行最后一次需求
        执行逻辑
        1：给目标集群的master和源集群master下发执行器
        2：在源集群master执行日志备份
        3：源和目标不在同一台机器上，则利用job传输备份文件（可选）
        4：恢复日志备份文件
        5：重新启动源master的例行备份逻辑（可选）
        6：更改迁移记录状态
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 计算源集群和目标集群的master
            info["dst_cluster_list"] = [info["dst_cluster"]]
            cluster = Cluster.objects.get(id=info["src_cluster"])
            target_clusters = Cluster.objects.filter(id__in=info["dst_cluster_list"])

            # 获取当前cluster的主节点,每个集群有且只有一个master/orphan 实例
            master_instance = cluster.storageinstance_set.get(
                instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
            )
            # 获取集群的备份路径
            backup_path = self.__calc_target_backup_path(cluster.id, master_instance.port, "incr")

            # 拼接子流程，子流程并发执行
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context["dts_infos"] = sub_flow_context.pop("rename_infos")
            sub_flow_context["target_backup_dir"] = backup_path
            sub_flow_context["job_id"] = f"dts_incr_{self.root_id}_{master_instance.port}"
            sub_flow_context["backup_dbs"] = [i["db_name"] for i in info["rename_infos"]]

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 创建随机账号
            sub_pipeline.add_act(
                act_name=_("create temp job account"),
                act_component_code=SqlserverAddJobUserComponent.code,
                kwargs=asdict(
                    CreateRandomJobUserKwargs(
                        cluster_ids=[cluster.id] + [c.id for c in target_clusters],
                        sid=create_sqlserver_login_sid(),
                    ),
                ),
            )

            # 给目标集群的master和源集群master下发执行器
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

            # 执行数据库日志备份
            sub_pipeline.add_act(
                act_name=_("在源集群[{}]执行数据库日志备份".format(master_instance.ip_port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=master_instance.machine.ip, bk_cloud_id=cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_backup_dbs_payload.__name__,
                        job_timeout=12 * 3600,
                        custom_params={
                            "port": master_instance.port,
                            "file_tag": SqlserverBackupFileTagEnum.INCREMENT_BACKUP.value,
                            "backup_type": SqlserverBackupMode.LOG_BACKUP.value,
                        },
                    )
                ),
                write_payload_var=SqlserverBackupIDContext.log_backup_id_var_name(),
            )
            # 对应目标集群恢复数据
            target_sub_pipelines = []
            for target_cluster in target_clusters:
                target_sub_pipelines.append(
                    self.__incr_restore_sub_flow(
                        sub_flow_context=sub_flow_context,
                        source_cluster=cluster,
                        source_instance=master_instance,
                        target_cluster=target_cluster,
                    )
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=target_sub_pipelines)

            if self.data["is_last"]:
                # 重新启动源master的例行备份逻辑
                sub_pipeline.add_act(
                    act_name=_("启动源master[{}]的backup jobs".format(master_instance.ip_port)),
                    act_component_code=ExecSqlserverBackupJobComponent.code,
                    kwargs=asdict(
                        ExecBackupJobsKwargs(cluster_id=cluster.id, exec_mode=SqlserverBackupJobExecMode.ENABLE),
                    ),
                )
            # 更改迁移记录状态
            sub_pipeline.add_act(
                act_name=_("更新任务状态"),
                act_component_code=SqlserverDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SqlserverDBMeta.update_dts_status.__name__,
                    )
                ),
            )

            # 删除随机账号
            sub_pipeline.add_act(
                act_name=_("remove temp job account"),
                act_component_code=SqlserverDropJobUserComponent.code,
                kwargs=asdict(DropRandomJobUserKwargs(cluster_ids=[cluster.id] + [c.id for c in target_clusters])),
            )

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("[{}]增量数据迁移流程".format(cluster.name))))

            # 更新root_id在迁移表上，并标记online状态
            SqlserverDtsInfo.objects.filter(id=info["dts_id"]).update(
                root_id=self.root_id, status=DtsStatus.IncrOnline
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline(init_trans_data_class=SqlserverBackupIDContext())

    def __full_restore_sub_flow(
        self,
        sub_flow_context: dict,
        target_cluster: Cluster,
        source_cluster: Cluster,
        source_instance: StorageInstance,
    ):
        """
        恢复数据的流程
        """
        # 声明子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
        target_master_instance = target_cluster.storageinstance_set.get(
            instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
        )

        # 这里计算出目标集群的恢复目录
        target_backup_path = self.__calc_target_backup_path(target_cluster.id, target_master_instance.port, "full")

        # 给目标集群的master发执行器
        sub_pipeline.add_act(
            act_name=_("下发执行器"),
            act_component_code=TransFileInWindowsComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    target_hosts=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                    file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                ),
            ),
        )

        if source_instance.machine.ip != target_master_instance.machine.ip:
            # 源和目标不在同一台机器上，则利用job传输备份文件
            sub_pipeline.add_act(
                act_name=_("传送文件到目标机器[{}]".format(target_master_instance.machine.ip)),
                act_component_code=SqlserverTransBackupFileFor2P2Component.code,
                kwargs=asdict(
                    P2PFileForWindowKwargs(
                        source_hosts=[Host(ip=source_instance.machine.ip, bk_cloud_id=source_cluster.bk_cloud_id)],
                        target_hosts=[
                            Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)
                        ],
                        file_target_path=target_backup_path,
                        cluster_id=source_cluster.id,
                    ),
                ),
            )

        # 恢复全量备份文件
        sub_pipeline.add_act(
            act_name=_("恢复全量备份数据[{}]".format(target_master_instance.ip_port)),
            act_component_code=RestoreForDtsComponent.code,
            kwargs=asdict(
                RestoreForDtsKwargs(
                    cluster_id=source_cluster.id,
                    job_id=sub_flow_context["job_id"],
                    restore_infos=sub_flow_context["dts_infos"],
                    restore_mode=SqlserverRestoreMode.FULL.value,
                    restore_db_status=SqlserverRestoreDBStatus.NORECOVERY.value,
                    restore_path=target_backup_path,
                    exec_ips=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                    port=target_master_instance.port,
                    job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                )
            ),
        )

        # 恢复日志备份文件
        if self.data["dts_mode"] == SqlserverDtsMode.INCR.value:
            restore_db_status = SqlserverRestoreDBStatus.NORECOVERY.value
        else:
            restore_db_status = SqlserverRestoreDBStatus.RECOVERY.value

        sub_pipeline.add_act(
            act_name=_("恢复增量备份数据[{}]".format(target_master_instance.ip_port)),
            act_component_code=RestoreForDtsComponent.code,
            kwargs=asdict(
                RestoreForDtsKwargs(
                    cluster_id=source_cluster.id,
                    job_id=sub_flow_context["job_id"],
                    restore_infos=sub_flow_context["dts_infos"],
                    restore_mode=SqlserverRestoreMode.LOG.value,
                    restore_db_status=restore_db_status,
                    restore_path=target_backup_path,
                    exec_ips=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                    port=target_master_instance.port,
                    job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                )
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=_("[{}]全量备份文件恢复子流程".format(target_cluster.name)))

    def __incr_restore_sub_flow(
        self,
        sub_flow_context: dict,
        target_cluster: Cluster,
        source_cluster: Cluster,
        source_instance: StorageInstance,
    ):
        """
        恢复增量备份数据的流程
        """
        # 声明子流程
        sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
        target_master_instance = target_cluster.storageinstance_set.get(
            instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
        )

        # 这里计算出目标集群的恢复目录
        target_backup_path = self.__calc_target_backup_path(target_cluster.id, target_master_instance.port, "incr")

        # 给目标集群的master发执行器
        sub_pipeline.add_act(
            act_name=_("下发执行器"),
            act_component_code=TransFileInWindowsComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    target_hosts=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                    file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                ),
            ),
        )

        if source_instance.machine.ip != target_master_instance.machine.ip:
            # 源和目标不在同一台机器上，则利用job传输备份文件
            sub_pipeline.add_act(
                act_name=_("传送文件到目标机器[{}]".format(target_master_instance.machine.ip)),
                act_component_code=SqlserverTransBackupFileFor2P2Component.code,
                kwargs=asdict(
                    P2PFileForWindowKwargs(
                        source_hosts=[Host(ip=source_instance.machine.ip, bk_cloud_id=source_cluster.bk_cloud_id)],
                        target_hosts=[
                            Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)
                        ],
                        file_target_path=target_backup_path,
                        cluster_id=source_cluster.id,
                        is_trans_full_backup=False,
                    ),
                ),
            )

        # 恢复日志备份文件
        if self.data["is_last"]:
            restore_db_status = SqlserverRestoreDBStatus.RECOVERY.value
        else:
            restore_db_status = SqlserverRestoreDBStatus.NORECOVERY.value

        sub_pipeline.add_act(
            act_name=_("恢复增量备份数据[{}]".format(target_master_instance.ip_port)),
            act_component_code=RestoreForDtsComponent.code,
            kwargs=asdict(
                RestoreForDtsKwargs(
                    cluster_id=source_cluster.id,
                    job_id=sub_flow_context["job_id"],
                    restore_infos=sub_flow_context["dts_infos"],
                    restore_mode=SqlserverRestoreMode.LOG.value,
                    restore_db_status=restore_db_status,
                    restore_path=target_backup_path,
                    exec_ips=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                    port=target_master_instance.port,
                    job_timeout=DBM_SQLSERVER_JOB_LONG_TIMEOUT,
                )
            ),
        )

        return sub_pipeline.build_sub_process(sub_name=_("[{}]增量备份文件恢复子流程".format(target_cluster.name)))
