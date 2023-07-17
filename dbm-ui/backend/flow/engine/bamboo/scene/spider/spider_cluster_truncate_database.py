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
import copy
import logging
from dataclasses import asdict
from typing import Dict, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.flow.consts import DBA_SYSTEM_USER
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
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.truncate_data_create_stage_database import (
    TruncateDataCreateStageDatabaseComponent,
)
from backend.flow.plugins.components.collections.mysql.truncate_data_generate_stage_database_name import (
    TruncateDataGenerateStageDatabaseNameComponent,
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
from backend.flow.plugins.components.collections.spider.truncate_database_drop_stage_db_via_ctl import (
    TruncateDatabaseDropStageDBViaCtlComponent,
)
from backend.flow.plugins.components.collections.spider.truncate_database_old_new_map_adapter_service import (
    TruncateDatabaseOldNewMapAdapterComponent,
)
from backend.flow.plugins.components.collections.spider.truncate_database_on_spider_via_ctl import (
    TruncateDatabaseOnSpiderViaCtlComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import BKCloudIdKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLTruncateDataContext

logger = logging.getLogger("flow")


class SpiderTruncateDatabaseFlow(object):
    """
    tendbcluster 清档
    1. 用中控建立备份库表
    2. 在 remote 上把备份库的所有表 drop 掉
    3. 在 remote 上做常规清档
    """

    def __init__(self, root_id: str, cluster_type: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data
        self.cluster_type = cluster_type

    def truncate_database(self):
        """
        self.data =
        {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "TENDBCLUSTER_TRUNCATE_DATABASE",
        "infos": [
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

        truncate_database_pipeline = Builder(root_id=self.root_id, data=self.data)
        cluster_pipes = []

        for job in self.data["infos"]:
            try:
                cluster_obj = Cluster.objects.get(
                    pk=job["cluster_id"], bk_biz_id=self.data["bk_biz_id"], cluster_type=self.cluster_type
                )
            except ObjectDoesNotExist:
                raise ClusterNotExistException(cluster_type=self.cluster_type, cluster_id=job["cluster_id"])

            cluster_pipe = SubBuilder(
                root_id=self.root_id,
                data={
                    **job,
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ticket_type": self.data["ticket_type"],
                    "ip": cluster_obj.proxyinstance_set.filter(
                        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                    )
                    .first()
                    .machine.ip,
                    "port": cluster_obj.proxyinstance_set.first().port,
                    "ctl_primary": cluster_obj.tendbcluster_ctl_primary_address(),
                },
            )

            cluster_pipe.add_act(
                act_name=_("构造过滤正则"),
                act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                kwargs={},
            )
            cluster_pipe.add_act(
                act_name=_("获得清档目标"),
                act_component_code=FilterDatabaseTableFromRegexComponent.code,
                kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            )

            if not job["force"]:
                cluster_pipe.add_sub_pipeline(
                    build_check_cluster_table_using_sub_flow(
                        root_id=self.root_id, cluster_obj=cluster_obj, parent_global_data=self.data
                    )
                )

            cluster_pipe.add_act(
                act_name=_("生成备份库名"), act_component_code=TruncateDataGenerateStageDatabaseNameComponent.code, kwargs={}
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

            # remote 上做常规清档
            truncate_on_remote_pipes = []
            for remote_master_instance in cluster_obj.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.MASTER.value
            ):
                shard_id = (
                    StorageInstanceTuple.objects.filter(ejector=remote_master_instance)
                    .first()
                    .tendbclusterstorageset.shard_id
                )
                logger.info("shard_id: {}".format(shard_id))

                on_remote_job = copy.deepcopy(job)
                # 库正则模式不以 % 结尾, 或者不是 "*" 时, 需要拼接 shard_id
                on_remote_job["db_patterns"] = [
                    ele if ele.endswith("%") or ele == "*" else "{}_{}".format(ele, shard_id)
                    for ele in on_remote_job["db_patterns"]
                ]
                on_remote_job["ignore_dbs"] = [
                    ele if ele.endswith("%") or ele == "*" else "{}_{}".format(ele, shard_id)
                    for ele in on_remote_job["ignore_dbs"]
                ]

                logger.info("on_remote_job: {}".format(on_remote_job))

                truncate_on_remote_pipe = SubBuilder(
                    root_id=self.root_id,
                    data={
                        **on_remote_job,
                        "uid": self.data["uid"],
                        "created_by": self.data["created_by"],
                        "bk_biz_id": self.data["bk_biz_id"],
                        "ticket_type": self.data["ticket_type"],
                        "ip": remote_master_instance.machine.ip,
                        "port": remote_master_instance.port,
                        "shard_id": shard_id,
                    },
                )

                truncate_on_remote_pipe.add_act(
                    act_name=_("构造过滤正则"),
                    act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                    kwargs={},
                )

                truncate_on_remote_pipe.add_act(
                    act_name=_("获得清档目标"),
                    act_component_code=FilterDatabaseTableFromRegexComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                truncate_on_remote_pipe.add_act(
                    act_name=_("适配备份库映射"),
                    act_component_code=TruncateDatabaseOldNewMapAdapterComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                truncate_on_remote_pipe.add_act(
                    act_name=_("重建备份库"),
                    act_component_code=TruncateDataCreateStageDatabaseComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                truncate_on_remote_pipe.add_act(
                    act_name=_("备份清档表"),
                    act_component_code=TruncateDataRenameTableComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
                )

                truncate_on_remote_pipe.add_act(
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
                truncate_on_remote_pipe.add_act(
                    act_name=_("备份库中其他对象"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            run_as_system_user=DBA_SYSTEM_USER,
                            exec_ip=remote_master_instance.machine.ip,
                            get_mysql_payload_func=MysqlActPayload.get_dump_na_table_payload.__name__,
                        )
                    ),
                )

                truncate_on_remote_pipes.append(
                    truncate_on_remote_pipe.build_sub_process(
                        sub_name=_("{} on remote {} 清档".format(cluster_obj.immute_domain, remote_master_instance))
                    )
                )

            cluster_pipe.add_parallel_sub_pipeline(sub_flow_list=truncate_on_remote_pipes)

            # 到这里, remote 上
            # 1. 源库中的所有东西都已经备份到 stage 库了
            # 2. 源库中没有表
            # 通过中控以集群基本处理源库
            cluster_pipe.add_act(
                act_name=_("处理集群表"),
                act_component_code=TruncateDatabaseOnSpiderViaCtlComponent.code,
                kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            )

            # 清档动作完成
            # 等待人工确认删除备份库
            cluster_pipe.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            cluster_pipe.add_act(
                act_name=_("删除备份库"),
                act_component_code=TruncateDatabaseDropStageDBViaCtlComponent.code,
                kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            )

            cluster_pipes.append(cluster_pipe.build_sub_process(sub_name=_("{} 清档".format(cluster_obj.immute_domain))))

        truncate_database_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        logger.info(_("构造清档流程成功"))
        truncate_database_pipeline.run_pipeline(init_trans_data_class=MySQLTruncateDataContext())
