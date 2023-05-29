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
from dataclasses import asdict
from typing import Dict, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException, MasterInstanceNotExistException
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_SYSTEM_USER, TruncateDataTypeEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.build_database_table_filter_regex import (
    DatabaseTableFilterRegexBuilderComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.filter_database_table_from_regex import (
    FilterDatabaseTableFromRegexComponent,
)
from backend.flow.plugins.components.collections.mysql.general_check_db_in_using import GeneralCheckDBInUsingComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.truncate_data_create_stage_database import (
    TruncateDataCreateStageDatabaseComponent,
)
from backend.flow.plugins.components.collections.mysql.truncate_data_drop_stage_database import (
    TruncateDataDropStageDatabaseComponent,
)
from backend.flow.plugins.components.collections.mysql.truncate_data_generate_stage_database_name import (
    TruncateDataGenerateStageDatabaseNameComponent,
)
from backend.flow.plugins.components.collections.mysql.truncate_data_recreate_table import (
    TruncateDataReCreateTableComponent,
)
from backend.flow.plugins.components.collections.mysql.truncate_data_rename_table import (
    TruncateDataRenameTableComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import BKCloudIdKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLTruncateDataContext

logger = logging.getLogger("flow")


class MySQLTruncateFlow(object):
    """
    TenDBHA 清档
    支持跨云操作
    """

    def __init__(self, root_id: str, cluster_type: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data
        self.cluster_type = cluster_type

    def truncate_flow(self):
        """
        self.data =
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "[MYSQL_HA_TRUNCATE_DATA, MYSQL_SINGLE_TRUNCATE_DATA]",
        "truncate_data_infos": [
            {
                "cluster_id": int,
                "db_patterns": ["db1%", "db2%"],
                "ignore_dbs": ["db11", "db12", "db23"],
                "table_patterns": ["tb_role%", "tb_mail%", "*"],
                "ignore_tables": ["tb_role1", "tb_mail10"],
                "truncate_data_type": "drop_database"
                "force": ture/false
            },
            ...
            ...
            ]
        }
        """
        cluster_ids = [job["cluster_id"] for job in self.data["infos"]]
        dup_cluster_ids = [item for item, count in collections.Counter(cluster_ids).items() if count > 1]
        if dup_cluster_ids:
            raise DBMetaException(message="duplicate clusters found: {}".format(dup_cluster_ids))

        truncate_pipeline = Builder(root_id=self.root_id, data=self.data)
        cluster_pipes = []
        for job in self.data["infos"]:
            try:
                cluster_obj = Cluster.objects.get(
                    pk=job["cluster_id"], bk_biz_id=self.data["bk_biz_id"], cluster_type=self.cluster_type
                )
                cluster_main_storage_instances = cluster_obj.main_storage_instances()
                if not cluster_main_storage_instances.exists():
                    raise MasterInstanceNotExistException(cluster_type=self.cluster_type, cluster_id=job["cluster_id"])
            except ObjectDoesNotExist:
                raise ClusterNotExistException(cluster_type=self.cluster_type, cluster_id=job["cluster_id"])

            cluster_pipe = SubBuilder(root_id=self.root_id, data=self.data)
            instance_pipes = []
            for main_storage_instance in cluster_main_storage_instances:
                instance_pipe = SubBuilder(
                    root_id=self.root_id,
                    data={
                        **job,
                        "uid": self.data["uid"],
                        "created_by": self.data["created_by"],
                        "bk_biz_id": self.data["bk_biz_id"],
                        "ticket_type": self.data["ticket_type"],
                        "ip": main_storage_instance.machine.ip,
                        "port": main_storage_instance.port,
                    },
                )

                instance_pipe.add_act(
                    act_name=_("构造过滤正则"),
                    act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                    kwargs={},
                )

                instance_pipe.add_act(
                    act_name=_("获得清档目标"),
                    act_component_code=FilterDatabaseTableFromRegexComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                if not job["force"]:
                    instance_pipe.add_act(
                        act_name=_("检查清档目标是否在用"),
                        act_component_code=GeneralCheckDBInUsingComponent.code,
                        kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                    )

                instance_pipe.add_act(
                    act_name=_("生成备份库名"),
                    act_component_code=TruncateDataGenerateStageDatabaseNameComponent.code,
                    kwargs={},
                )

                instance_pipe.add_act(
                    act_name=_("建立备份库"),
                    act_component_code=TruncateDataCreateStageDatabaseComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                instance_pipe.add_act(
                    act_name=_("备份清档表"),
                    act_component_code=TruncateDataRenameTableComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                if job["truncate_data_type"] == TruncateDataTypeEnum.TRUNCATE_TABLE.value:
                    instance_pipe.add_act(
                        act_name=_("重建空表"),
                        act_component_code=TruncateDataReCreateTableComponent.code,
                        kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                    )

                if job["truncate_data_type"] == TruncateDataTypeEnum.DROP_DATABASE.value:
                    instance_pipe.add_act(
                        act_name=_("下发actuator介质"),
                        act_component_code=TransFileComponent.code,
                        kwargs=asdict(
                            DownloadMediaKwargs(
                                bk_cloud_id=cluster_obj.bk_cloud_id,
                                exec_ip=main_storage_instance.machine.ip,
                                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                            )
                        ),
                    )

                    instance_pipe.add_act(
                        act_name=_("备份库中其他对象"),
                        act_component_code=ExecuteDBActuatorScriptComponent.code,
                        kwargs=asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=cluster_obj.bk_cloud_id,
                                run_as_system_user=DBA_SYSTEM_USER,
                                exec_ip=main_storage_instance.machine.ip,
                                get_mysql_payload_func=MysqlActPayload.get_dump_na_table_payload.__name__,
                            )
                        ),
                    )

                instance_pipe.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

                instance_pipe.add_act(
                    act_name=_("删除备份库"),
                    act_component_code=TruncateDataDropStageDatabaseComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                instance_pipes.append(
                    instance_pipe.build_sub_process(
                        sub_name=_("{} {} 清档".format(cluster_obj.immute_domain, main_storage_instance))
                    )
                )

            cluster_pipe.add_parallel_sub_pipeline(sub_flow_list=instance_pipes)
            cluster_pipes.append(cluster_pipe.build_sub_process(sub_name=_("{} 清档".format(cluster_obj.immute_domain))))

        truncate_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        logger.info(_("构建清档流程成功"))
        truncate_pipeline.run_pipeline(init_trans_data_class=MySQLTruncateDataContext())
