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
from dataclasses import asdict
from typing import Dict, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_SYSTEM_USER, TruncateDataTypeEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.build_database_table_filter_regex import (
    DatabaseTableFilterRegexBuilderComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.filter_database_table_from_regex import (
    FilterDatabaseTableFromRegexComponent,
)
from backend.flow.plugins.components.collections.mysql.general_check_db_in_using import GeneralCheckDBInUsingComponent
from backend.flow.plugins.components.collections.mysql.mysql_ha_db_table_backup_response import (
    MySQLHaDatabaseTableBackupResponseComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    BKCloudIdKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    ExecActuatorKwargsForPool,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLFullBackupContext

logger = logging.getLogger("flow")


class MySQLHAFullBackupFlow(object):
    """
    mysql 库表备份流程
    支持跨云管理

    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def full_backup_flow(self):
        """
        self.data = {
        "uid": "398346234",
        "created_type": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_HA_FULL_BACKUP",
        "infos": {
            "online": bool, # Todo 测试 --- 废弃
            "backup_type": enum of backend.flow.consts.MySQLBackupTypeEnum
            "file_tag": enum of backend.flow.consts.MySQLBackupFileTagEnum
            "cluster_ids": List[int],
        }
        }

        这个单据默认, 强制, 不可选的在第一个 slave 上备份
        """
        cluster_ids = self.data["infos"]["cluster_ids"]

        backup_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipes = []
        for cluster_id in cluster_ids:

            try:
                cluster_obj = Cluster.objects.get(
                    pk=cluster_id, bk_biz_id=self.data["bk_biz_id"], cluster_type=ClusterType.TenDBHA.value
                )

                slave_obj = cluster_obj.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.SLAVE.value
                ).first()

            except ObjectDoesNotExist:
                raise Exception(
                    "bk_biz_id = {}, cluster_id = {}, cluster_type = {} not found".format(
                        self.data["bk_biz_id"], cluster_id, ClusterType.TenDBHA.value
                    )
                )

            sub_pipe = SubBuilder(
                root_id=self.root_id,
                data={
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ticket_type": self.data["ticket_type"],
                    "ip": slave_obj.machine.ip,
                    "port": slave_obj.port,
                    # "charset": self.data["infos"]["charset"],
                    "file_tag": self.data["infos"]["file_tag"],
                    "backup_type": self.data["infos"]["backup_type"],
                    "db_patterns": ["*"],
                    "table_patterns": ["*"],
                    "ignore_dbs": [],
                    "ignore_tables": [],
                },
            )

            # if not self.data["infos"]["online"]:
            #     sub_pipe.add_act(
            #         act_name=_("构造过滤正则"),
            #         act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
            #         kwargs={},
            #     )
            #
            #     sub_pipe.add_act(
            #         act_name=_("获得源目标的库表"),
            #         act_component_code=FilterDatabaseTableFromRegexComponent.code,
            #         kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            #     )
            #
            #     sub_pipe.add_act(
            #         act_name=_("检查源数据库是否在用"),
            #         act_component_code=GeneralCheckDBInUsingComponent.code,
            #         kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            #     )

            sub_pipe.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        exec_ip=slave_obj.machine.ip,
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
                        exec_ip=slave_obj.machine.ip,
                        get_mysql_payload_func=MysqlActPayload.get_full_backup_payload.__name__,
                    )
                ),
                write_payload_var="backup_report_response",
            )

            sub_pipe.add_act(
                act_name=_("关联备份id"),
                act_component_code=MySQLHaDatabaseTableBackupResponseComponent.code,
                kwargs={},
            )

            sub_pipes.append(sub_pipe.build_sub_process(sub_name=_("{} 全库备份").format(cluster_obj.immute_domain)))

        backup_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipes)
        logger.info(_("构建全库备份流程成功"))
        backup_pipeline.run_pipeline(init_trans_data_class=MySQLFullBackupContext())
