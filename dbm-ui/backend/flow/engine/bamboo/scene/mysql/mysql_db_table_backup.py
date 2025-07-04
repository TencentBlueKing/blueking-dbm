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
import logging
import uuid
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_SYSTEM_USER, LONG_JOB_TIMEOUT
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.build_database_table_filter_regex import (
    DatabaseTableFilterRegexBuilderComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.filter_database_table_from_regex import (
    FilterDatabaseTableFromRegexComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_link_backup_id_bill_id import (
    MySQLLinkBackupIdBillIdComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import BKCloudIdKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLBackupDemandContext

logger = logging.getLogger("flow")


class MySQLDBTableBackupFlow(object):
    """
    支持跨云操作
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def backup_flow(self):
        """
        self.data =
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_DB_TABLE_BACKUP",
        "infos": [
            {
                "cluster_id": int,
                "db_patterns": ["db1%", "db2%"],
                "ignore_dbs": ["db11", "db12", "db23"],
                "table_patterns": ["tb_role%", "tb_mail%", "*"],
                "ignore_tables": ["tb_role1", "tb_mail10"],
            },
            ...
            ...
            ]
        }
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        # 合并重复集群
        merged_jobs = defaultdict(list)
        for job in self.data["infos"]:
            cluster_id = job["cluster_id"]
            merged_jobs[cluster_id].append(job)

        backup_pipeline = Builder(root_id=self.root_id, data=self.data)
        cluster_flows = []
        for cluster_id, jobs in merged_jobs.items():
            cluster_flows.append(
                self._build_cluster_sub_flow(
                    cluster_id=cluster_id,
                    jobs=jobs,
                ).build_sub_process(sub_name=_("{} 库表备份".format(Cluster.objects.get(id=cluster_id).immute_domain)))
            )

        backup_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_flows)
        logger.info(_("构建库表备份流程成功"))
        backup_pipeline.run_pipeline(init_trans_data_class=MySQLBackupDemandContext())

    def _build_cluster_sub_flow(self, cluster_id: int, jobs: List):
        cluster_obj = Cluster.objects.get(pk=cluster_id, bk_biz_id=self.data["bk_biz_id"])
        if cluster_obj.cluster_type == ClusterType.TenDBHA:
            instance_obj = cluster_obj.storageinstance_set.get(
                instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True, status=InstanceStatus.RUNNING
            )
        else:
            instance_obj = cluster_obj.storageinstance_set.filter(status=InstanceStatus.RUNNING).first()

        cluster_flow = SubBuilder(root_id=self.root_id, data=self.data)
        cluster_flow.add_act(
            act_name=_("下发actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=cluster_obj.bk_cloud_id,
                    exec_ip=instance_obj.machine.ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        for job in jobs:
            job_flow = SubBuilder(
                root_id=self.root_id,
                data={
                    **job,
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ticket_type": self.data["ticket_type"],
                    "ip": instance_obj.machine.ip,
                    "port": instance_obj.port,
                    "backup_id": uuid.uuid1(),
                    "backup_type": "logical",
                    "backup_gsd": ["schema", "data"],
                    "custom_backup_dir": "backupDatabaseTable",
                    "role": instance_obj.instance_role,
                },
            )
            job_flow.add_act(
                act_name=_("构造mydumper正则"),
                act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                kwargs={},
            )
            job_flow.add_act(
                act_name=_("检查正则匹配"),
                act_component_code=FilterDatabaseTableFromRegexComponent.code,
                kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            )
            job_flow.add_act(
                act_name=_("执行库表备份"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        job_timeout=LONG_JOB_TIMEOUT,
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        exec_ip=instance_obj.machine.ip,
                        get_mysql_payload_func=MysqlActPayload.mysql_backup_demand_payload.__name__,
                    )
                ),
            )
            job_flow.add_act(
                act_name=_("关联备份id"),
                act_component_code=MySQLLinkBackupIdBillIdComponent.code,
                kwargs={},
            )

            subflow_name = "include db: {}, exclude db: {}, include table: {}, exclude table: {}".format(
                job["db_patterns"], job["ignore_dbs"], job["table_patterns"], job["ignore_tables"]
            )
            cluster_flow.add_sub_pipeline(sub_flow=job_flow.build_sub_process(sub_name=_(subflow_name)))

        return cluster_flow
