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

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.exceptions import IncompatibleBackupTypeAndLocal, MySQLBackupLocalException
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_link_backup_id_bill_id import (
    MySQLLinkBackupIdBillIdComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLBackupDemandContext

logger = logging.getLogger("flow")


class TenDBClusterFullBackupFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def full_backup_flow(self):
        """
        self.data = {
        "uid": "398346234",
        "created_type": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "SPIDER_FULL_BACKUP",
        "infos": {
            "backup_type": enum of backend.flow.consts.MySQLBackupTypeEnum
            "file_tag": enum of backend.flow.consts.MySQLBackupFileTagEnum
            “clusters": [
              {
                "id": int,
                "backup_local": enum TenDBBackupLocation::[REMOTE, SPIDER_MNT],
                "spider_mnt_address": "x.x.x.x:y" # 如果 backup_local 是 spider_mnt
              },
              ...
            ],
        }
        }
        """

        clusters = self.data["infos"]["clusters"]

        backup_pipeline = Builder(root_id=self.root_id, data=self.data)

        cluster_pipes = []
        for cluster in clusters:
            if self.data["infos"]["backup_type"] == "physical" and cluster["backup_local"] == "spider_mnt":
                IncompatibleBackupTypeAndLocal(
                    backup_type=self.data["infos"]["backup_type"], backup_local=cluster["backup_local"]
                )

            try:
                cluster_obj = Cluster.objects.get(
                    pk=cluster["id"],
                    bk_biz_id=self.data["bk_biz_id"],
                    cluster_type=ClusterType.TenDBCluster.value,
                )
            except ObjectDoesNotExist:
                raise ClusterNotExistException(
                    cluster_type=ClusterType.TenDBCluster.value, cluster_id=cluster["id"], immute_domain=""
                )

            backup_id = uuid.uuid1()
            cluster_pipe = SubBuilder(
                root_id=self.root_id,
                data={
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ticket_type": self.data["ticket_type"],
                    "backup_id": backup_id,
                    "file_tag": self.data["infos"]["file_tag"],
                    "backup_type": self.data["infos"]["backup_type"],
                },
            )

            cluster_pipe.add_sub_pipeline(
                sub_flow=self.backup_on_spider_ctl(backup_id=backup_id, cluster_obj=cluster_obj)
            )

            if cluster["backup_local"] == "remote":
                cluster_pipe.add_parallel_sub_pipeline(
                    sub_flow_list=self.backup_on_remote(backup_id=backup_id, cluster_obj=cluster_obj)
                )
            elif cluster["backup_local"] == "spider_mnt":
                cluster_pipe.add_sub_pipeline(
                    sub_flow=self.backup_on_spider_mnt(
                        backup_id=backup_id, cluster_obj=cluster_obj, spider_mnt_address=cluster["spider_mnt_address"]
                    )
                )
            else:
                raise MySQLBackupLocalException(msg=_("不支持的备份位置 {}".format(cluster["backup_local"])))

            cluster_pipe.add_act(
                act_name=_("关联备份id"),
                act_component_code=MySQLLinkBackupIdBillIdComponent.code,
                kwargs={},
            )

            cluster_pipes.append(cluster_pipe.build_sub_process(sub_name=_("{} 全备".format(cluster_obj.immute_domain))))

        backup_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        logger.info(_("构造全库备份流程成功"))
        backup_pipeline.run_pipeline(init_trans_data_class=MySQLBackupDemandContext())

    def backup_on_spider_ctl(self, backup_id: uuid.UUID, cluster_obj: Cluster) -> SubProcess:
        ctl_primary_address = cluster_obj.tendbcluster_ctl_primary_address()
        ctl_primary_ip, ctl_primary_port = ctl_primary_address.split(IP_PORT_DIVIDER)

        on_ctl_sub_pipe = SubBuilder(
            root_id=self.root_id,
            data={
                "uid": self.data["uid"],
                "created_by": self.data["created_by"],
                "bk_biz_id": self.data["bk_biz_id"],
                "ticket_type": self.data["ticket_type"],
                "ip": ctl_primary_ip,
                "port": cluster_obj.proxyinstance_set.first().port,
                "backup_id": backup_id,
                "backup_type": "logical",
                "backup_gsd": ["schema"],
                "file_tag": self.data["infos"]["file_tag"],
            },
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
            act_name=_("spider 执行全库备份"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster_obj.bk_cloud_id,
                    run_as_system_user=DBA_SYSTEM_USER,
                    exec_ip=ctl_primary_ip,
                    get_mysql_payload_func=MysqlActPayload.mysql_backup_demand_payload.__name__,
                )
            ),
        )

        on_ctl_sub_pipe.add_act(
            act_name=_("ctl 执行全库备份"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster_obj.bk_cloud_id,
                    run_as_system_user=DBA_SYSTEM_USER,
                    exec_ip=ctl_primary_ip,
                    get_mysql_payload_func=MysqlActPayload.mysql_backup_demand_payload_on_ctl.__name__,
                )
            ),
        )
        return on_ctl_sub_pipe.build_sub_process(sub_name=_("spider/ctl备份库表结构"))

    def backup_on_remote(self, backup_id: uuid.UUID, cluster_obj: Cluster) -> List[SubProcess]:
        on_slave_pipes = []
        stand_by_slaves = defaultdict(list)
        for tp in StorageInstanceTuple.objects.filter(
            ejector__cluster=cluster_obj,
            receiver__cluster=cluster_obj,
            ejector__instance_inner_role=InstanceInnerRole.MASTER.value,
            receiver__instance_inner_role=InstanceInnerRole.SLAVE.value,
            receiver__is_stand_by=True,
        ):
            stand_by_slaves[tp.receiver.machine.ip].append(
                {"port": tp.receiver.port, "shard_id": tp.tendbclusterstorageset.shard_id}
            )

        for ip, dtls in stand_by_slaves.items():
            for dtl in dtls:
                on_slave_pipe = SubBuilder(
                    root_id=self.root_id,
                    data={
                        "uid": self.data["uid"],
                        "created_by": self.data["created_by"],
                        "bk_biz_id": self.data["bk_biz_id"],
                        "ticket_type": self.data["ticket_type"],
                        "backup_id": backup_id,
                        "file_tag": self.data["infos"]["file_tag"],
                        "backup_type": self.data["infos"]["backup_type"],
                        "ip": ip,
                        "port": dtl["port"],
                        "backup_gsd": ["schema", "data"],
                    },
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
                    act_name=_("remote 执行全库备份"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            run_as_system_user=DBA_SYSTEM_USER,
                            exec_ip=ip,
                            get_mysql_payload_func=MysqlActPayload.mysql_backup_demand_payload.__name__,
                        )
                    ),
                )

                on_slave_pipes.append(on_slave_pipe.build_sub_process(sub_name=_("remote 全库备份")))
        return on_slave_pipes

    def backup_on_spider_mnt(self, backup_id: uuid.UUID, cluster_obj: Cluster, spider_mnt_address: str) -> SubProcess:
        spider_mnt_ip, spider_mnt_port = spider_mnt_address.split(IP_PORT_DIVIDER)
        spider_mnt_port = int(spider_mnt_port)

        on_spider_mnt_pipe = SubBuilder(
            root_id=self.root_id,
            data={
                "uid": self.data["uid"],
                "created_by": self.data["created_by"],
                "bk_biz_id": self.data["bk_biz_id"],
                "ticket_type": self.data["ticket_type"],
                "ip": spider_mnt_ip,
                "port": spider_mnt_port,
                "backup_id": backup_id,
                "backup_type": "logical",
                "backup_gsd": ["schema", "data"],
            },
        )

        on_spider_mnt_pipe.add_act(
            act_name=_("下发actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=cluster_obj.bk_cloud_id,
                    exec_ip=spider_mnt_ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        on_spider_mnt_pipe.add_act(
            act_name=_("运维节点执行全库备份"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    bk_cloud_id=cluster_obj.bk_cloud_id,
                    run_as_system_user=DBA_SYSTEM_USER,
                    exec_ip=spider_mnt_ip,
                    get_mysql_payload_func=MysqlActPayload.mysql_backup_demand_payload.__name__,
                )
            ),
        )
        return on_spider_mnt_pipe.build_sub_process(sub_name=_("spider_mnt全库备份"))
