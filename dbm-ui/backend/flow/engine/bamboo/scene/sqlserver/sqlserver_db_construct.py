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
from datetime import datetime

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.sqlserver.rollback.handlers import SQLServerRollbackHandler
from backend.flow.consts import SqlserverRestoreDBStatus
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.sqlserver.base_flow import BaseFlow
from backend.flow.engine.bamboo.scene.sqlserver.common_sub_flow import download_backup_file_sub_flow
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptComponent
from backend.flow.plugins.components.collections.sqlserver.trans_files import TransFileInWindowsComponent
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import (
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    SqlserverDBConstructContext,
)
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_host import Host
from backend.utils.time import str2datetime, trans_time_zone

logger = logging.getLogger("flow")


class SqlserverDataConstruct(BaseFlow):
    """
    构建Sqlserver数据构造的流程类
    数据构造指的是拿取历史备份记录来进行做数据构造，可以执行原地构造以及远程构造
    兼容跨云集群的执行
    """

    @staticmethod
    def _get_full_backup_infos(restore_full_backup_files: list, rename_infos: list, target_path: str):
        """
        计算一些场景用到全量备份信息
        """
        full_download_infos = []
        full_restore_infos = []
        for info in rename_infos:
            for file_info in restore_full_backup_files:
                if info["db_name"] == file_info["dbname"]:
                    # 匹配到构造数据库对应的备份文件信息，录入
                    full_download_infos.append(
                        {
                            "file_path": file_info["local_path"],
                            "file_name": file_info["file_name"],
                            "task_id": file_info["task_id"],
                        }
                    )
                    full_restore_infos.append(
                        {
                            "db_name": info["db_name"],
                            "target_db_name": info["target_db_name"],
                            "bak_file": f"{target_path}{file_info['file_name']}",
                            "backup_full_start_time": file_info["backup_begin_time"],
                            "backup_full_end_time": file_info["backup_end_time"],
                        }
                    )
                    break

        return full_download_infos, full_restore_infos

    @staticmethod
    def _get_log_backup_infos(full_restore_infos: list, restore_time: datetime, cluster_id: int, target_path: str):
        """
        根据时间范围计算出需要的log_backup文件
        """
        log_download_infos = []
        log_restore_infos = []
        for full_info in full_restore_infos:
            log_backup_infos = SQLServerRollbackHandler(cluster_id=cluster_id).query_binlogs(
                str2datetime(full_info["backup_full_end_time"]), restore_time, full_info["db_name"]
            )

            if not log_backup_infos:
                raise Exception(
                    f"the log-backup-list is empty: "
                    f"cluster_id:[{cluster_id}], "
                    f"start_time:[{full_info['backup_full_end_time']}]"
                    f"end_time:[{restore_time}]"
                    f"db_name:[{full_info['db_name']}]"
                )

            for file in log_backup_infos:
                log_download_infos.append(
                    {"file_path": file["local_path"], "file_name": file["file_name"], "task_id": file["task_id"]}
                )
            log_restore_infos.append(
                {
                    "db_name": full_info["db_name"],
                    "target_db_name": full_info["target_db_name"],
                    "bak_file": [f"{target_path}{i['file_name']}" for i in log_backup_infos],
                }
            )
        return log_download_infos, log_restore_infos

    def run_flow(self):
        """
        执行逻辑：
        1: 下发执行器
        1: 获取相关的备份信息
        2: 下载相关备份文件
        3: 恢复文件
        """

        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []

        for info in self.data["infos"]:
            # 计算源集群和目标集群的master
            cluster = Cluster.objects.get(id=info["src_cluster"])
            target_cluster = Cluster.objects.get(id=info["dst_cluster"])
            target_master_instance = target_cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)

            # 计算构造需要的一些信息
            target_dir = f"d:\\dbbak\\data_construct_{self.root_id}\\"
            full_download_infos, restore_full_backup_infos = self._get_full_backup_infos(
                restore_full_backup_files=info["restore_backup_file"]["logs"],
                rename_infos=info["rename_infos"],
                target_path=target_dir,
            )

            # 拼接子流程，子流程并发执行
            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("infos")
            sub_flow_context.update(info)
            sub_flow_context["target_dir"] = target_dir

            # 声明子流程
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))

            # 下发执行器
            sub_pipeline.add_act(
                act_name=_("下发执行器到目标集群master[{}]".format(target_master_instance.machine.ip)),
                act_component_code=TransFileInWindowsComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        target_hosts=[
                            Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)
                        ],
                        file_list=GetFileList(db_type=DBType.Sqlserver).get_db_actuator_package(),
                    ),
                ),
            )

            # 下载全量备份文件
            sub_pipeline.add_sub_pipeline(
                sub_flow=download_backup_file_sub_flow(
                    uid=self.data["uid"],
                    root_id=self.root_id,
                    backup_file_list=full_download_infos,
                    target_path=sub_flow_context["target_dir"],
                    target_instance=target_master_instance,
                    write_payload_var=SqlserverDBConstructContext.full_backup_infos_var_name(),
                    sub_name=_("下载全量备份文件到目标集群master[{}]".format(target_master_instance.machine.ip)),
                )
            )

            # 如果定点构造，恢复日志备份
            if info.get("restore_time", "") != "":

                # 要查询log_backup日志
                log_download_infos, restore_log_backup_infos = self._get_log_backup_infos(
                    full_restore_infos=restore_full_backup_infos,
                    restore_time=str2datetime(info["restore_time"]),
                    cluster_id=cluster.id,
                    target_path=target_dir,
                )

                # 下载日志备份文件
                sub_pipeline.add_sub_pipeline(
                    sub_flow=download_backup_file_sub_flow(
                        uid=self.data["uid"],
                        root_id=self.root_id,
                        backup_file_list=log_download_infos,
                        target_path=sub_flow_context["target_dir"],
                        target_instance=target_master_instance,
                        write_payload_var=SqlserverDBConstructContext.log_backup_infos_var_name(),
                        sub_name=_("下载日志备份文件到目标集群master[{}]".format(target_master_instance.machine.ip)),
                    )
                )

            # 恢复全量备份文件
            if info.get("restore_time", "") != "":
                restore_mode = SqlserverRestoreDBStatus.NORECOVERY.value
            else:
                restore_mode = SqlserverRestoreDBStatus.RECOVERY.value

            sub_pipeline.add_act(
                act_name=_("恢复全量备份数据[{}]".format(target_master_instance.ip_port)),
                act_component_code=SqlserverActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ips=[Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)],
                        get_payload_func=SqlserverActPayload.get_restore_full_dbs_payload.__name__,
                        job_timeout=3 * 3600,
                        custom_params={
                            "port": target_master_instance.port,
                            "restore_infos": restore_full_backup_infos,
                            "restore_mode": restore_mode,
                        },
                    )
                ),
            )

            # 如果定点构造，恢复日志备份
            if info.get("restore_time", "") != "":

                sub_pipeline.add_act(
                    act_name=_("恢复日志备份数据[{}]".format(target_master_instance.ip_port)),
                    act_component_code=SqlserverActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            exec_ips=[
                                Host(ip=target_master_instance.machine.ip, bk_cloud_id=target_cluster.bk_cloud_id)
                            ],
                            get_payload_func=SqlserverActPayload.get_restore_log_dbs_payload.__name__,
                            job_timeout=3 * 3600,
                            custom_params={
                                "port": target_master_instance.port,
                                "restore_infos": restore_log_backup_infos,
                                "restore_mode": SqlserverRestoreDBStatus.RECOVERY.value,
                                "restore_time": trans_time_zone(
                                    str2datetime(info["restore_time"]), cluster.time_zone
                                ).strftime("%Y-%m-%dT%H:%M:%S"),
                            },
                        )
                    ),
                )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("[{}]->[{}]数据构造流程".format(cluster.name, target_cluster.name))
                )
            )

        main_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        main_pipeline.run_pipeline(init_trans_data_class=SqlserverDBConstructContext())
