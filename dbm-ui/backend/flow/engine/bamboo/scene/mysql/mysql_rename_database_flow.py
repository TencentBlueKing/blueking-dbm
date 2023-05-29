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
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import ClusterNotExistException, MasterInstanceNotExistException
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
from backend.flow.plugins.components.collections.mysql.rename_database_confirm_empty_from import (
    RenameDatabaseConfirmEmptyFromComponent,
)
from backend.flow.plugins.components.collections.mysql.rename_database_drop_from import RenameDatabaseDropFromComponent
from backend.flow.plugins.components.collections.mysql.rename_database_prepare_param import (
    RenameDatabasePrepareParamComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.truncate_data_create_stage_database import (
    TruncateDataCreateStageDatabaseComponent,
)
from backend.flow.plugins.components.collections.mysql.truncate_data_rename_table import (
    TruncateDataRenameTableComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import BKCloudIdKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLTruncateDataContext

logger = logging.getLogger("flow")


class MySQLRenameDatabaseFlow(object):
    """
    mysql 重命名database流程
    支持多云区域操作
    增加单据临时ADMIN账号的添加和删除逻辑
    """

    def __init__(self, root_id: str, cluster_type: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data
        self.cluster_type = cluster_type

    def rename_database(self):
        """
        self.data =
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "[MYSQL_HA_RENAME_DATABASE, MYSQL_SINGLE_RENAME_DATABASE]",
        "infos": [
            {
                "cluster_id": int,
                "from_database": str,
                "to_database": str
                "force": bool
            },
            ...
            ...
            ]
        }
        """

        merged_jobs = defaultdict(list)
        for job in self.data["infos"]:
            cluster_id = job["cluster_id"]
            merged_jobs[cluster_id].append(
                {"from_database": job["from_database"], "to_database": job["to_database"], "force": job["force"]}
            )

        cluster_ids = [i["cluster_id"] for i in self.data["infos"]]
        rename_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids))
        )
        cluster_pipes = []
        for cluster_id in merged_jobs:
            jobs = merged_jobs[cluster_id]  # 这东西是个 List [{from, to, force}, {from, to, force}]

            try:
                cluster_obj = Cluster.objects.get(
                    pk=cluster_id, bk_biz_id=self.data["bk_biz_id"], cluster_type=self.cluster_type
                )
                cluster_main_storage_instances = cluster_obj.main_storage_instances()
                if not cluster_main_storage_instances.exists():
                    raise MasterInstanceNotExistException(cluster_type=self.cluster_type, cluster_id=cluster_id)
            except ObjectDoesNotExist:
                raise ClusterNotExistException(cluster_type=self.cluster_type, cluster_id=cluster_id)

            cluster_pipe = SubBuilder(root_id=self.root_id, data=self.data)
            instance_pipes = []
            for main_storage_instance in cluster_main_storage_instances:
                instance_pipe = SubBuilder(
                    root_id=self.root_id,
                    data={
                        "jobs": jobs,
                        "uid": self.data["uid"],
                        "created_by": self.data["created_by"],
                        "bk_biz_id": self.data["bk_biz_id"],
                        "ticket_type": self.data["ticket_type"],
                        "ip": main_storage_instance.machine.ip,
                        "port": main_storage_instance.port,
                        "truncate_data_type": TruncateDataTypeEnum.DROP_DATABASE.value,  # 为了复用 truncate data 的 service
                        "db_patterns": [
                            job["from_database"] for job in jobs
                        ],  # [job["from_database"]],  # 为了复用 truncate data 的 service
                        "ignore_dbs": [],
                        "table_patterns": ["*"],
                        "ignore_tables": [],
                    },
                )

                # 构造 old_new_map
                instance_pipe.add_act(
                    act_name=_("准备重命名参数"),
                    act_component_code=RenameDatabasePrepareParamComponent.code,
                    kwargs={},
                )

                instance_pipe.add_act(
                    act_name=_("构造过滤正则"),
                    act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                    kwargs={},
                )

                instance_pipe.add_act(
                    act_name=_("获得源目标的库表"),
                    act_component_code=FilterDatabaseTableFromRegexComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                # from 和 to 的存在性检查 frontend saas 做了

                # force 其实一个单据都是一样的, 所以随便取一个就行了
                if not jobs[0]["force"]:
                    instance_pipe.add_act(
                        act_name=_("检查源数据库是否在用"),
                        act_component_code=GeneralCheckDBInUsingComponent.code,
                        kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                    )

                instance_pipe.add_act(
                    act_name=_("建立目标数据库"),
                    act_component_code=TruncateDataCreateStageDatabaseComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                instance_pipe.add_act(
                    act_name=_("表迁移"),
                    act_component_code=TruncateDataRenameTableComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

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
                    act_name=_("迁移源库中其他对象"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            exec_ip=main_storage_instance.machine.ip,
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            run_as_system_user=DBA_SYSTEM_USER,
                            get_mysql_payload_func=MysqlActPayload.get_dump_na_table_payload.__name__,
                        )
                    ),
                )

                instance_pipe.add_act(
                    act_name=_("确认源数据库已空"),
                    act_component_code=RenameDatabaseConfirmEmptyFromComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )
                instance_pipe.add_act(
                    act_name=_("删除源数据库"),
                    act_component_code=RenameDatabaseDropFromComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                instance_pipes.append(
                    instance_pipe.build_sub_process(
                        sub_name=_("{} {} 重命名数据库".format(cluster_obj.immute_domain, main_storage_instance))
                    )
                )

            cluster_pipe.add_parallel_sub_pipeline(sub_flow_list=instance_pipes)
            cluster_pipes.append(
                cluster_pipe.build_sub_process(sub_name=_("{} 重命名数据库").format(cluster_obj.immute_domain))
            )

        rename_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        logger.info(_("构建重命名数据库流程成功"))
        rename_pipeline.run_pipeline(init_trans_data_class=MySQLTruncateDataContext(), is_drop_random_user=True)
