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
from datetime import datetime
from typing import Dict, Optional

from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend import env
from backend.components.dbresource.client import DBResourceApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_services.cmdb.biz import get_or_create_resource_module
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.machine_os_init import insert_host_event
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_cluster_config
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_data_sub_flow import rollback_remote_and_backupid
from backend.flow.engine.bamboo.scene.mysql.mysql_single_apply_flow import MySQLSingleApplyFlow
from backend.flow.engine.bamboo.scene.mysql.mysql_single_destroy_flow import MySQLSingleDestroyFlow
from backend.flow.plugins.components.collections.common.external_service import ExternalServiceComponent
from backend.flow.plugins.components.collections.common.transfer_host_service import TransferHostServiceComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_backup_recovery_exercise import (
    MySQLBackupRecoverTaskMetaComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_os_init import CleanDataBakDirComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SingleApplyManualContext


class MySQLRollbackExerciseFlow(object):
    """
    MySQL Rollback Exercise Flow

    This class implements the complete workflow for MySQL database rollback exercise.
    It handles the following operations:
    1. Deploying a temporary MySQL instance for rollback testing
    2. Restoring backup data to the temporary instance
    3. Verifying the rollback results
    4. Cleaning up resources after exercise

    The workflow consists of multiple sub-pipelines executed in sequence:
    - MySQL instance deployment
    - Backup data restoration
    - Resource cleanup
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        Initialize the rollback exercise flow

        Args:
            root_id (str): Unique identifier for the workflow instance
            data (Dict): Ticket data containing rollback parameters:
                {
                    "ticket_type": "MYSQL_ROLLBACK_EXERCISE",  # Ticket type identifier
                    "exercise_cluster_id": 1,  # ID of cluster to rollback
                    "backup_id": "xxx",  # Backup ID to restore from
                    "rollback_host": {  # Target host for rollback exercise
                        "ip": "127.0.0.1",  # IP address
                        "bk_host_id": 1212,  # Host ID in CMDB
                        "bk_cloud_id": 0  # Cloud area ID
                    },
                    "bk_biz_id": 123,  # Target business ID
                    "backupinfo": {},  # Backup metadata
                    "labels": [""]  # Resource labels
                }
        """
        self.root_id = root_id
        self.ticket_data = data
        self.data = {}
        self.rollback_port = 20000
        self.rollback_host = self.ticket_data["rollback_host"]
        self.rollback_to_bk_biz_id = self.ticket_data["bk_biz_id"]
        self.labels = self.ticket_data.get("labels", [])

    def run(self):
        """
        Execute the complete rollback exercise workflow

        The workflow consists of the following steps:
        1. Prepare temporary MySQL instance:
            - Get cluster metadata
            - Generate unique cluster name
            - Prepare installation parameters
            - Deploy temporary MySQL instance

        2. Perform backup restoration:
            - Create backup directory
            - Restore backup data
            - Update task status

        3. Clean up resources:
            - Destroy temporary instance
            - Return host to resource pool
            - Update final task status

        The workflow uses Bamboo pipeline to orchestrate all steps with proper
        error handling and status tracking.
        """
        pipeline = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
        )
        cluster_class = Cluster.objects.get(id=self.ticket_data["exercise_cluster_id"])
        if cluster_class.cluster_type == ClusterType.TenDBCluster.value:
            shard0 = cluster_class.tendbclusterstorageset_set.filter(shard_id=0).first()
            master = shard0.storage_instance_tuple.ejector
        else:
            filters = Q(
                cluster__cluster_type=ClusterType.TenDBSingle.value, instance_inner_role=InstanceInnerRole.ORPHAN.value
            )
            filters = filters | Q(
                cluster__cluster_type=ClusterType.TenDBHA.value, instance_inner_role=InstanceInnerRole.MASTER.value
            )
            master = cluster_class.storageinstance_set.filter(filters).first()
        self.data = copy.deepcopy(self.ticket_data)
        self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
        self.data["db_module_id"] = cluster_class.db_module_id
        self.data["time_zone"] = cluster_class.time_zone
        self.data["created_by"] = self.ticket_data["created_by"]
        self.data["module"] = cluster_class.db_module_id
        self.data["ticket_type"] = self.ticket_data["ticket_type"]
        self.data["uid"] = self.ticket_data["uid"]
        self.data["city"] = cluster_class.region
        self.data["package"] = Package.get_latest_package(
            version=cluster_class.major_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL
        ).name
        self.data["charset"], self.data["db_version"] = get_version_and_charset(
            cluster_class.bk_biz_id,
            db_module_id=self.data["db_module_id"],
            cluster_type=cluster_class.cluster_type,
        )
        install_ticket = copy.deepcopy(self.data)
        datetime_str = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S%f")
        cluster_name = "{}-{}".format(cluster_class.name, datetime_str).replace("_", "")
        if len(cluster_name) > 48:
            cluster_name = get_random_string(24)
        master_domain = "rollback.{}.dba.db".format(cluster_name)
        install_ticket["start_mysql_port"] = self.rollback_port
        install_ticket["inst_num"] = 1
        install_ticket["ticket_type"] = self.ticket_data["ticket_type"]
        sql = """show global variables where Variable_name in ('sql_mode','max_allowed_packet','lower_case_table_names',
        'innodb_strict_mode','max_heap_table_size','tmp_table_size','character_set_server','collation_server',
        'default_storage_engine','default-storage-engine')"""
        old_instance_configs = get_cluster_config(cluster_class, query_cmds=sql)
        install_ticket["apply_infos"] = [
            {
                "new_ip": self.rollback_host,
                "old_instance_configs": {str(master.port): old_instance_configs},
                "clusters": [{"name": cluster_name, "master": master_domain}],
            }
        ]
        # 初始化安装mysql
        pipeline.add_sub_pipeline(
            MySQLSingleApplyFlow(root_id=self.root_id, data=install_ticket).deploy_mysql_single_flow(
                origin_cluster_domain=cluster_class.immute_domain
            )
        )
        # 更新任务状态
        pipeline.add_act(
            act_name=_("更新演练任务状态"),
            act_component_code=MySQLBackupRecoverTaskMetaComponent.code,
            kwargs={
                "task_id": self.root_id,
                "task_status": "deploy_success",
            },
            is_remote_rewritable=True,
        )
        mycluster = {
            "bk_cloud_id": cluster_class.bk_cloud_id,
            "databases": ["*"],
            "tables": ["*"],
            "databases_ignore": [],
            "tables_ignore": [],
            "charset": self.data["charset"],
            "change_master": False,
            "cluster_type": cluster_class.cluster_type,
            "file_target_path": "/data/dbbak/{}/{}".format(self.root_id, master.port),
            "skip_local_exists": True,
            "backupinfo": self.data["backupinfo"],
            "rollback_ip": self.rollback_host["ip"],
            "rollback_port": self.rollback_port,
        }
        # 创建目录
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=cluster_class.bk_cloud_id,
            cluster_type=None,
            cluster=mycluster,
        )
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
        exec_act_kwargs.exec_ip = self.rollback_host["ip"]
        pipeline.add_act(
            act_name=_("创建目录 {}".format(mycluster["file_target_path"])),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
            is_remote_rewritable=True,
        )
        # 回档备份文件
        pipeline.add_sub_pipeline(
            sub_flow=rollback_remote_and_backupid(
                root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=mycluster
            )
        )
        # 更新演练任务状态
        pipeline.add_act(
            act_name=_("更新演练任务状态"),
            act_component_code=MySQLBackupRecoverTaskMetaComponent.code,
            kwargs={
                "task_id": self.root_id,
                "task_status": "recover_success",
            },
            is_remote_rewritable=True,
        )
        # 回档成功,回收资源
        uninstall_data = copy.deepcopy(self.data)
        uninstall_data["force"] = True
        pipeline.add_sub_pipeline(
            MySQLSingleDestroyFlow(root_id=self.root_id, data=uninstall_data).destroy_mysql_single_subflow(
                ip=self.rollback_host["ip"],
                port=self.rollback_port,
                bk_cloud_id=cluster_class.bk_cloud_id,
                domain=master_domain,
                bk_biz_id=self.rollback_to_bk_biz_id,
            )
        )
        # 退还资源到资源池
        import_data = {
            "resource_type": "mysql",
            "for_biz": self.rollback_to_bk_biz_id,
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "hosts": [
                {
                    "ip": self.rollback_host["ip"],
                    "host_id": self.rollback_host["bk_host_id"],
                    "bk_cloud_id": self.rollback_host["bk_cloud_id"],
                }
            ],
            "labels": self.labels,
            "operator": "system",
        }
        pipeline.add_act(
            act_name=_("机器归还到资源池"),
            act_component_code=ExternalServiceComponent.code,
            kwargs={
                "params": import_data,
                "api_import_path": DBResourceApi.__module__,
                "api_import_module": "DBResourceApi",
                "api_call_func": "resource_import",
                "success_callback_path": f"{insert_host_event.__module__}.{insert_host_event.__name__}",
            },
            is_remote_rewritable=True,
        )
        # 清理数据备份目录
        pipeline.add_act(
            act_name=_("清理数据备份目录"),
            act_component_code=CleanDataBakDirComponent.code,
            kwargs={
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_cloud_id": self.rollback_host["bk_cloud_id"],
                "exec_ip": self.rollback_host["ip"],
            },
            is_remote_rewritable=True,
        )
        # 转移模块到对应业务的资源池
        pipeline.add_act(
            act_name=_("主机转移至资源池空闲模块"),
            act_component_code=TransferHostServiceComponent.code,
            kwargs={
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_module_ids": [get_or_create_resource_module()],
                "bk_host_ids": [self.rollback_host["bk_host_id"]],
                "update_host_properties": {"dbm_meta": [], "need_monitor": False, "update_operator": False},
            },
            is_remote_rewritable=True,
        )
        pipeline.add_act(
            act_name=_("更新演练任务状态"),
            act_component_code=MySQLBackupRecoverTaskMetaComponent.code,
            kwargs={
                "task_id": self.root_id,
                "task_status": "resource_return_success",
            },
            is_remote_rewritable=True,
        )
        # run pipeline
        pipeline.run_pipeline(init_trans_data_class=SingleApplyManualContext())
