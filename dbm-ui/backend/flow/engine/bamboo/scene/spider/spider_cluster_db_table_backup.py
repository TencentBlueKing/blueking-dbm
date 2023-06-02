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
import logging
import uuid
from collections import Counter, defaultdict
from typing import Dict, Optional

from dataclasses import asdict
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaBaseException
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.build_database_table_filter_regex import \
    DatabaseTableFilterRegexBuilderComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_ha_db_table_backup_response import (
    MySQLHaDatabaseTableBackupResponseComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLTableBackupContext

logger = logging.getLogger("flow")
class TenDBClusterDBTableBackupFlow(object):
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
        "ticket_type": "SPIDER_DB_TABLE_BACKUP",
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
        dup_cluster_ids = [item for item, count in Counter(cluster_ids).items() if count > 1]
        if dup_cluster_ids:
            raise DBMetaBaseException(message="duplicate clusters found: {}".format(dup_cluster_ids))

        backup_pipeline = Builder(root_id=self.root_id, data=self.data)

        cluster_pipes = []
        for job in self.data["infos"]:
            try:
                cluster_obj = Cluster.objects.get(
                    pk=job["cluster_id"], bk_biz_id=self.data["bk_biz_id"], cluster_type=ClusterType.TenDBCluster.value
                )
            except ObjectDoesNotExist:
                raise ClusterNotExistException(cluster_type = ClusterType.TenDBCluster.value,
                                               cluster_id = job["cluster_id"],
                                               immute_domain="")

            backup_id = uuid.uuid1()
            cluster_pipe = SubBuilder(
                root_id=self.root_id,
                data={
                    **job,
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ticket_type": self.data["ticket_type"],
                    "backup_id": backup_id,
                }
            )


            # 在 ctl_primary 上备份 spider 表结构和中控表结构
            ctl_primary_address = cluster_obj.tendbcluster_ctl_primary_address()
            ctl_primary_ip, ctl_primary_port = ctl_primary_address.split(IP_PORT_DIVIDER)

            on_ctl_sub_pipe = SubBuilder(
                root_id=self.root_id,
                data={
                    **job,
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ticket_type": self.data["ticket_type"],
                    "ip": ctl_primary_ip,
                    "port": cluster_obj.proxyinstance_set.first().port,
                    "backup_id": backup_id,
                }
            )

            on_ctl_sub_pipe.add_act(
                act_name=_("构造 spider/ctl mydumper正则"),
                act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                kwargs={},
            )

            on_ctl_sub_pipe.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        exec_ip=ctl_primary_ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            on_ctl_sub_pipe.add_act(
                act_name=_("spider 执行库表备份"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        exec_ip=ctl_primary_ip,
                        get_mysql_payload_func=MysqlActPayload.get_db_table_backup_payload.__name__,
                    )
                ),
            )

            on_ctl_sub_pipe.add_act(
                act_name=_("ctl 执行库表备份"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        exec_ip=ctl_primary_ip,
                        get_mysql_payload_func=MysqlActPayload.get_db_table_backup_payload_on_ctl.__name__,
                    )
                ),
            )

            cluster_pipe.add_sub_pipeline(sub_flow=on_ctl_sub_pipe.build_sub_process(
                sub_name=_("spider/ctl 备份库表结构".format())))

            # 在 所有 is_stand_by slave 上备份数据
            # slave 上的备份同机器串行
            on_slave_pipes = []
            stand_by_slaves = defaultdict(list)
            for tp in StorageInstanceTuple.objects.filter(
                ejector__cluster=cluster_obj,
                receiver__cluster=cluster_obj,
                ejector__instance_inner_role=InstanceInnerRole.MASTER.value,
                receiver__instance_inner_role=InstanceInnerRole.SLAVE.value,
                receiver__is_stand_by=True
            ):
                stand_by_slaves[tp.receiver.machine.ip].append({
                    "port": tp.receiver.port,
                    "shard_id": tp.tendbclusterstorageset.shard_id
                })

            for ip, dtls in stand_by_slaves.items():
                for dtl in dtls:
                    on_slave_job = copy.deepcopy(job)
                    on_slave_job["db_patterns"] = [
                        ele if ele.endswith("%") else "{}_{}".format(ele, dtl["shard_id"]) for ele in
                        on_slave_job["db_patterns"]
                    ]
                    on_slave_job["ignore_dbs"] = [
                        ele if ele.endswith("%") else "{}_{}".format(ele, dtl["shard_id"]) for ele in
                        on_slave_job["ignore_dbs"]
                    ]

                    on_slave_pipe = SubBuilder(
                        root_id = self.root_id,
                        data = {
                            **on_slave_job,
                            "uid": self.data["uid"],
                            "created_by": self.data["created_by"],
                            "bk_biz_id": self.data["bk_biz_id"],
                            "ticket_type": self.data["ticket_type"],
                            "ip": ip,
                            "port": dtl["port"],
                            "backup_id": backup_id,
                        }
                    )

                    on_slave_pipe.add_act(
                        act_name=_("构造remote mydumper正则"),
                        act_component_code=DatabaseTableFilterRegexBuilderComponent.code,
                        kwargs={},
                    )

                    on_slave_pipe.add_act(
                        act_name=_("下发actuator介质"),
                        act_component_code=TransFileComponent.code,
                        kwargs=asdict(
                            DownloadMediaKwargs(
                                bk_cloud_id=cluster_obj.bk_cloud_id,
                                exec_ip=ip,
                                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                            )
                        ),
                    )

                    on_slave_pipe.add_act(
                        act_name=_("remote 执行库表备份"),
                        act_component_code=ExecuteDBActuatorScriptComponent.code,
                        kwargs=asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=cluster_obj.bk_cloud_id,
                                run_as_system_user=DBA_SYSTEM_USER,
                                exec_ip=ip,
                                get_mysql_payload_func=MysqlActPayload.get_db_table_backup_payload.__name__,
                            )
                        ),
                    )

                    on_slave_pipes.append(on_slave_pipe.build_sub_process(sub_name=_("remote 备份库表")))

            cluster_pipe.add_parallel_sub_pipeline(sub_flow_list=on_slave_pipes)

            cluster_pipe.add_act(
                act_name=_("关联备份id"),
                act_component_code=MySQLHaDatabaseTableBackupResponseComponent.code,
                kwargs={},
            )

            cluster_pipes.append(cluster_pipe.build_sub_process(
                sub_name=_("{} 库表备份".format(cluster_obj.immute_domain))))

        backup_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        logger.info(_("构造库表备份流程成功"))
        backup_pipeline.run_pipeline(init_trans_data_class=MySQLTableBackupContext())