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
import collections
import logging
import uuid
from dataclasses import asdict
from typing import Dict, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaBaseException
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.build_database_table_filter_regex import (
    DatabaseTableFilterRegexBuilderComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_ha_db_table_backup_response import (
    MySQLHaDatabaseTableBackupResponseComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLTableBackupContext

logger = logging.getLogger("flow")


class MySQLHADBTableBackupFlow(object):
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
        "ticket_type": "MYSQL_HA_DB_TABLE_BACKUP",
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
        """
        cluster_ids = [job["cluster_id"] for job in self.data["infos"]]
        dup_cluster_ids = [item for item, count in collections.Counter(cluster_ids).items() if count > 1]
        if dup_cluster_ids:
            raise DBMetaBaseException(message="duplicate clusters found: {}".format(dup_cluster_ids))

        backup_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipes = []
        for job in self.data["infos"]:
            try:
                cluster_obj = Cluster.objects.get(
                    pk=job["cluster_id"], bk_biz_id=self.data["bk_biz_id"], cluster_type=ClusterType.TenDBHA.value
                )
            except ObjectDoesNotExist:
                raise ClusterNotExistException(
                    cluster_type=ClusterType.TenDBHA.value, cluster_id=job["cluster_id"], immute_domain=""
                )

            try:
                instance_obj = cluster_obj.storageinstance_set.get(
                    instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
                )
            except ObjectDoesNotExist:
                raise DBMetaBaseException(message=_("{} standby slave 不存在".format(cluster_obj.immute_domain)))

            sub_pipe = SubBuilder(
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
                },
            )

            sub_pipe.add_act(
                act_name=_("构造mydumper正则"),
                act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                kwargs={},
            )

            sub_pipe.add_act(
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

            sub_pipe.add_act(
                act_name=_("执行库表备份"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        exec_ip=instance_obj.machine.ip,
                        get_mysql_payload_func=MysqlActPayload.get_db_table_backup_payload.__name__,
                    )
                ),
                # write_payload_var="backup_report_response",
            )

            sub_pipe.add_act(
                act_name=_("关联备份id"),
                act_component_code=MySQLHaDatabaseTableBackupResponseComponent.code,
                kwargs={},
            )

            sub_pipes.append(sub_pipe.build_sub_process(sub_name=_("{} 库表备份").format(cluster_obj.immute_domain)))

        backup_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipes)
        logger.info(_("构建库表备份流程成功"))
        backup_pipeline.run_pipeline(init_trans_data_class=MySQLTableBackupContext())
