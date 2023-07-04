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
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstanceTuple
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
from backend.flow.plugins.components.collections.spider.check_cluster_table_using_sub import (
    build_check_cluster_table_using_sub_flow,
)
from backend.flow.plugins.components.collections.spider.clear_database_on_remote_service import (
    ClearDatabaseOnRemoteComponent,
)
from backend.flow.plugins.components.collections.spider.create_database_like_via_ctl import (
    CreateDatabaseLikeViaCtlComponent,
)
from backend.flow.plugins.components.collections.spider.drop_spider_table_via_ctl import DropSpiderTableViaCtlComponent
from backend.flow.utils.mysql.mysql_act_dataclass import BKCloudIdKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLTruncateDataContext

logger = logging.getLogger("flow")


class SpiderRenameDatabaseFlow(object):
    """
    tendbcluster 重命名 database
    1. 用中控建立备份库表
    2. 在 remote 上把备份库的所有表 drop 掉
    3. 在 remote 上做常规的 (类似 TendbHA) 的 rename database 操作
    4. 用中控只 drop 掉 spider 上老库下的 表, 存储过程, 触发器, 视图 ( admin = 0)
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
        "ticket_type": "SPIDER_RENAME_DATABASE",
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

        rename_pipeline = Builder(root_id=self.root_id, data=self.data)
        cluster_pipes = []
        for cluster_id in merged_jobs:
            jobs = merged_jobs[cluster_id]  # 这东西是个 List [{from, to, force}, {from, to, force}]

            try:
                cluster_obj = Cluster.objects.get(
                    pk=cluster_id, bk_biz_id=self.data["bk_biz_id"], cluster_type=self.cluster_type
                )
            except ObjectDoesNotExist:
                raise ClusterNotExistException(cluster_type=self.cluster_type, cluster_id=cluster_id)

            # 操作中控, 完成在 spider 上建库表, 并把 remote 上的新库 drop 掉
            cluster_pipe = SubBuilder(
                root_id=self.root_id,
                data={
                    "jobs": jobs,
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ticket_type": self.data["ticket_type"],
                    "ip": cluster_obj.immute_domain,
                    "port": cluster_obj.proxyinstance_set.first().port,
                    "ctl_primary": cluster_obj.tendbcluster_ctl_primary_address(),
                    "truncate_data_type": TruncateDataTypeEnum.DROP_DATABASE.value,  # 为了复用 truncate data 的 service
                    "db_patterns": [job["from_database"] for job in jobs],  # 为了复用 truncate data 的 service
                    "ignore_dbs": [],
                    "table_patterns": ["*"],
                    "ignore_tables": [],
                },
            )

            cluster_pipe.add_act(
                act_name=_("准备重命名参数"),
                act_component_code=RenameDatabasePrepareParamComponent.code,
                kwargs={},
            )

            cluster_pipe.add_act(
                act_name=_("构造过滤正则"),
                act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                kwargs={},
            )

            cluster_pipe.add_act(
                act_name=_("获得源目标的库表"),
                act_component_code=FilterDatabaseTableFromRegexComponent.code,
                kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            )

            # 在所有 spider 上检查库表是否在用
            if not jobs[0]["force"]:
                cluster_pipe.add_sub_pipeline(
                    build_check_cluster_table_using_sub_flow(
                        root_id=self.root_id, cluster_obj=cluster_obj, parent_global_data=self.data
                    )
                )

            cluster_pipe.add_act(
                act_name=_("建立备份库"),
                act_component_code=CreateDatabaseLikeViaCtlComponent.code,
                kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            )

            drop_on_remote_pipes = []
            for remote_master_instance in cluster_obj.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.MASTER.value
            ):

                shard_id = (
                    StorageInstanceTuple.objects.filter(ejector=remote_master_instance)
                    .first()
                    .tendbclusterstorageset.shard_id
                )

                on_remote_pipe = SubBuilder(
                    root_id=self.root_id,
                    data={
                        "ip": remote_master_instance.machine.ip,
                        "port": remote_master_instance.port,
                        "shard_id": shard_id,
                    },
                )
                on_remote_pipe.add_act(
                    act_name=_("预清理备份库"),
                    act_component_code=ClearDatabaseOnRemoteComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )
                drop_on_remote_pipes.append(on_remote_pipe.build_sub_process(sub_name=_("预清理备份库")))

            cluster_pipe.add_parallel_sub_pipeline(sub_flow_list=drop_on_remote_pipes)

            # remote 上做常规 mysql rename database
            rename_on_remote_pipes = []
            for remote_master_instance in cluster_obj.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.MASTER.value
            ):

                shard_id = (
                    StorageInstanceTuple.objects.filter(ejector=remote_master_instance)
                    .first()
                    .tendbclusterstorageset.shard_id
                )

                on_remote_jobs = [
                    {
                        "from_database": "{}_{}".format(ele["from_database"], shard_id),
                        "to_database": "{}_{}".format(ele["to_database"], shard_id),
                    }
                    for ele in jobs
                ]

                rename_on_remote_pipe = SubBuilder(
                    root_id=self.root_id,
                    data={
                        "jobs": on_remote_jobs,
                        "uid": self.data["uid"],
                        "created_by": self.data["created_by"],
                        "bk_biz_id": self.data["bk_biz_id"],
                        "ticket_type": self.data["ticket_type"],
                        "ip": remote_master_instance.machine.ip,
                        "port": remote_master_instance.port,
                        "truncate_data_type": TruncateDataTypeEnum.DROP_DATABASE.value,
                        "db_patterns": [
                            job["from_database"] for job in on_remote_jobs
                        ],  # 为了复用 truncate data 的 service
                        "ignore_dbs": [],
                        "table_patterns": ["*"],
                        "ignore_tables": [],
                    },
                )

                # 构造 old_new_map
                rename_on_remote_pipe.add_act(
                    act_name=_("准备重命名参数"),
                    act_component_code=RenameDatabasePrepareParamComponent.code,
                    kwargs={},
                )

                rename_on_remote_pipe.add_act(
                    act_name=_("构造过滤正则"),
                    act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                    kwargs={},
                )

                rename_on_remote_pipe.add_act(
                    act_name=_("获得源目标的库表"),
                    act_component_code=FilterDatabaseTableFromRegexComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                rename_on_remote_pipe.add_act(
                    act_name=_("建立目标数据库"),
                    act_component_code=TruncateDataCreateStageDatabaseComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                rename_on_remote_pipe.add_act(
                    act_name=_("表迁移"),
                    act_component_code=TruncateDataRenameTableComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                rename_on_remote_pipe.add_act(
                    act_name=_("下发actuator介质"),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            exec_ip=remote_master_instance.machine.ip,
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                )

                rename_on_remote_pipe.add_act(
                    act_name=_("迁移源库中其他对象"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            exec_ip=remote_master_instance.machine.ip,
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            run_as_system_user=DBA_SYSTEM_USER,
                            get_mysql_payload_func=MysqlActPayload.get_dump_na_table_payload.__name__,
                        )
                    ),
                )

                rename_on_remote_pipe.add_act(
                    act_name=_("确认源数据库已空"),
                    act_component_code=RenameDatabaseConfirmEmptyFromComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )
                rename_on_remote_pipe.add_act(
                    act_name=_("删除源数据库"),
                    act_component_code=RenameDatabaseDropFromComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                rename_on_remote_pipes.append(
                    rename_on_remote_pipe.build_sub_process(
                        sub_name=_("{} on remote {} 重命名数据库".format(cluster_obj.immute_domain, remote_master_instance))
                    )
                )

            cluster_pipe.add_parallel_sub_pipeline(sub_flow_list=rename_on_remote_pipes)

            # 中控 drop old database
            cluster_pipe.add_act(
                act_name=_("删除集群源库"),
                act_component_code=DropSpiderTableViaCtlComponent.code,
                kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            )

            cluster_pipes.append(
                cluster_pipe.build_sub_process(sub_name=_("{} 库表重命名".format(cluster_obj.immute_domain)))
            )

        rename_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        logger.info(_("构造数据库重命名流程成功"))
        rename_pipeline.run_pipeline(init_trans_data_class=MySQLTruncateDataContext())
