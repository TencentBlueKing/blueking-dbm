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

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.flow.consts import RollbackType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import install_mysql_in_cluster_sub_flow
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_data_sub_flow import (
    rollback_local_and_backupid,
    rollback_local_and_time,
    rollback_remote_and_backupid,
    rollback_remote_and_time,
    uninstall_instance_sub_flow,
)
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs
from backend.flow.utils.mysql.common.mysql_cluster_info import get_cluster_info, get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLRollbackDataFlow(object):
    """
    mysql 定点回档
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.ticket_data = data
        self.data = {}

    def rollback_data_flow(self):
        """
        定义重建slave节点的流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [i["cluster_id"] for i in self.data["infos"]]
        mysql_restore_slave_pipeline = Builder(
            root_id=self.root_id, data=copy.deepcopy(self.data), need_random_pass_cluster_ids=list(set(cluster_ids))
        )
        sub_pipeline_list = []
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_class = Cluster.objects.get(id=self.data["cluster_id"])
            master = cluster_class.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
            self.data["bk_biz_id"] = cluster_class.bk_biz_id
            self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
            self.data["db_module_id"] = cluster_class.db_module_id
            self.data["time_zone"] = cluster_class.time_zone
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["module"] = self.ticket_data["module"]
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["cluster_type"] = cluster_class.cluster_type
            self.data["uid"] = self.ticket_data["uid"]
            # self.data["package"] = Package.get_latest_package(
            #     version=cluster_class.major_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL
            # )
            self.data["package"] = cluster_class.major_version
            self.data["db_version"] = cluster_class.major_version
            self.data["force"] = info.get("force", False)
            self.data["charset"], self.data["db_version"] = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=self.data["db_module_id"],
                cluster_type=self.data["cluster_type"],
            )

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_mysql_in_cluster_sub_flow(
                    uid=self.ticket_data["uid"],
                    root_id=self.root_id,
                    cluster=cluster_class,
                    new_mysql_list=[self.data["rollback_ip"]],
                    install_ports=[master.port],
                )
            )
            cluster = {
                "install_ip": self.data["rollback_ip"],
                "cluster_ids": [cluster_class.id],
                "package": self.data["package"],
            }
            sub_pipeline.add_act(
                act_name=_("写入初始化实例的db_meta元信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.slave_recover_add_instance.__name__,
                        cluster=copy.deepcopy(cluster),
                        is_update_trans_data=False,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("安装backup-client工具"),
                act_component_code=DownloadBackupClientComponent.code,
                kwargs=asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=cluster_class.bk_cloud_id,
                        bk_biz_id=int(cluster_class.bk_biz_id),
                        download_host_list=[self.data["rollback_ip"]],
                    )
                ),
            )

            exec_act_kwargs = ExecActuatorKwargs(
                cluster=cluster,
                bk_cloud_id=cluster_class.bk_cloud_id,
                cluster_type=cluster_class.cluster_type,
                get_mysql_payload_func=MysqlActPayload.get_install_tmp_db_backup_payload.__name__,
            )
            exec_act_kwargs.exec_ip = [self.data["rollback_ip"]]
            sub_pipeline.add_act(
                act_name=_("安装临时备份程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            one_cluster = get_cluster_info(self.data["cluster_id"])
            one_cluster["rollback_ip"] = self.data["rollback_ip"]
            one_cluster["databases"] = self.data["databases"]
            one_cluster["tables"] = self.data["tables"]
            one_cluster["databases_ignore"] = self.data["databases_ignore"]
            one_cluster["tables_ignore"] = self.data["tables_ignore"]
            one_cluster["backend_port"] = one_cluster["master_port"]
            one_cluster["charset"] = self.data["charset"]
            one_cluster["change_master"] = False
            one_cluster["file_target_path"] = "/data/dbbak/{}/{}".format(self.root_id, master.port)
            one_cluster["skip_local_exists"] = True
            one_cluster["name_regex"] = "^.+{}\\.\\d+(\\..*)*$".format(one_cluster["master_port"])
            one_cluster["rollback_time"] = self.data["rollback_time"]
            one_cluster["rollback_ip"] = self.data["rollback_ip"]
            one_cluster["rollback_port"] = master.port
            one_cluster["rollback_time"] = self.data["rollback_time"]
            one_cluster["backupinfo"] = self.data["backupinfo"]
            one_cluster["rollback_type"] = self.data["rollback_type"]

            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=cluster_class.bk_cloud_id,
                cluster_type=ClusterType.TenDBHA,
                cluster=one_cluster,
            )
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
            exec_act_kwargs.exec_ip = self.data["rollback_ip"]
            sub_pipeline.add_act(
                act_name=_("创建目录 {}".format(one_cluster["file_target_path"])),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 本地备份+时间
            if self.data["rollback_type"] == RollbackType.LOCAL_AND_TIME:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_local_and_time(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=one_cluster
                    )
                )

            # 远程备份+时间
            elif self.data["rollback_type"] == RollbackType.REMOTE_AND_TIME.value:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_remote_and_time(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=one_cluster
                    )
                )
            # 远程备份+备份ID
            elif self.data["rollback_type"] == RollbackType.REMOTE_AND_BACKUPID.value:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_remote_and_backupid(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=one_cluster
                    )
                )

            # 本地备份+备份ID
            elif self.data["rollback_type"] == RollbackType.LOCAL_AND_BACKUPID:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_local_and_backupid(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=one_cluster
                    )
                )
            else:
                raise NormalTenDBFlowException(message=_("rollback_type不存在"))

            # 设置暂停。接下来卸载数据库的流程
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            sub_pipeline.add_sub_pipeline(
                sub_flow=uninstall_instance_sub_flow(
                    root_id=self.root_id, ticket_data=self.data, cluster_info=one_cluster
                )
            )
            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("定点恢复")))

        mysql_restore_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_slave_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)
