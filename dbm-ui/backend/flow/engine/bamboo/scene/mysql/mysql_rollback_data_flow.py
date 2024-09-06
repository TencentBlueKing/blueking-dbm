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
import logging.config
from dataclasses import asdict
from datetime import datetime
from typing import Dict, Optional

from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.flow.consts import InstanceStatus, MediumEnum, RollbackType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.common.get_local_backup import check_storage_database
from backend.flow.engine.bamboo.scene.mysql.common.mysql_resotre_data_sub_flow import mysql_rollback_data_sub_flow
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_data_sub_flow import (
    rollback_local_and_backupid,
    rollback_remote_and_backupid,
    rollback_remote_and_time,
)
from backend.flow.engine.bamboo.scene.mysql.mysql_single_apply_flow import MySQLSingleApplyFlow
from backend.flow.engine.bamboo.scene.spider.common.exceptions import NormalSpiderFlowException
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import ClusterInfoContext

logger = logging.getLogger("flow")


class MySQLRollbackDataFlow(object):
    """
    mysql 定点回档
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.ticket_data = data
        self.data = {}

    def rollback_data_flow(self):
        """
        定义重建slave节点的流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [i["cluster_id"] for i in self.ticket_data["infos"]]
        mysql_restore_slave_pipeline = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        sub_pipeline_list = []
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_class = Cluster.objects.get(id=self.data["cluster_id"])
            filters = Q(cluster_type=ClusterType.TenDBSingle.value, instance_inner_role=InstanceInnerRole.ORPHAN.value)
            filters = filters | Q(
                cluster_type=ClusterType.TenDBHA.value, instance_inner_role=InstanceInnerRole.MASTER.value
            )
            master = cluster_class.storageinstance_set.get(filters)
            self.data["bk_biz_id"] = cluster_class.bk_biz_id
            self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
            self.data["db_module_id"] = cluster_class.db_module_id
            self.data["time_zone"] = cluster_class.time_zone
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["module"] = cluster_class.db_module_id
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["cluster_type"] = cluster_class.cluster_type
            self.data["uid"] = self.ticket_data["uid"]
            self.data["city"] = cluster_class.region
            self.data["package"] = Package.get_latest_package(
                version=cluster_class.major_version, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL
            ).name
            self.data["db_version"] = cluster_class.major_version
            self.data["force"] = info.get("force", False)
            self.data["charset"], self.data["db_version"] = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=self.data["db_module_id"],
                cluster_type=self.data["cluster_type"],
            )
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
            install_ticket = copy.deepcopy(self.data)
            datetime_str = datetime.strftime(datetime.now(), "%Y%m%d%H%M%S%f")
            cluster_name = "{}-{}".format(cluster_class.name, datetime_str)
            if len(cluster_name) > 48:
                cluster_name = get_random_string(24)
            master_domain = "tmpdb.{}.dba.db".format(cluster_name)
            install_ticket["start_mysql_port"] = master.port
            install_ticket["inst_num"] = 1
            install_ticket["ticket_type"] = self.ticket_data["ticket_type"]
            install_ticket["apply_infos"] = [
                {"new_ip": self.data["bk_rollback"], "clusters": [{"name": cluster_name, "master": master_domain}]}
            ]
            sub_pipeline.add_sub_pipeline(
                MySQLSingleApplyFlow(root_id=self.root_id, data=install_ticket).deploy_mysql_single_flow()
            )

            mycluster = {
                "name": cluster_class.name,
                "cluster_id": cluster_class.id,
                "cluster_type": cluster_class.cluster_type,
                "bk_biz_id": cluster_class.bk_biz_id,
                "bk_cloud_id": cluster_class.bk_cloud_id,
                "db_module_id": cluster_class.db_module_id,
                "databases": self.data["databases"],
                "tables": self.data["tables"],
                "databases_ignore": self.data["databases_ignore"],
                "tables_ignore": self.data["tables_ignore"],
                "charset": self.data["charset"],
                "change_master": False,
                "file_target_path": "/data/dbbak/{}/{}".format(self.root_id, master.port),
                "skip_local_exists": True,
                "name_regex": "^.+{}\\.\\d+(\\..*)*$".format(master.port),
                "rollback_time": self.data["rollback_time"],
                "backupinfo": self.data["backupinfo"],
                "rollback_type": self.data["rollback_type"],
                "rollback_ip": self.data["rollback_ip"],
                "rollback_port": master.port,
                "backend_port": master.port,
                "master_port": master.port,
                "master_ip": master.machine.ip,
            }

            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=cluster_class.bk_cloud_id,
                cluster_type=ClusterType.TenDBHA,
                cluster=mycluster,
            )
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
            exec_act_kwargs.exec_ip = self.data["rollback_ip"]
            sub_pipeline.add_act(
                act_name=_("创建目录 {}".format(mycluster["file_target_path"])),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 本地备份+时间
            if self.data["rollback_type"] == RollbackType.LOCAL_AND_TIME:
                inst_list = ["{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER, master.port)]
                stand_by_slaves = cluster_class.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.SLAVE.value,
                    is_stand_by=True,
                    status=InstanceStatus.RUNNING.value,
                ).exclude(machine__ip__in=[self.data["rollback_ip"]])
                if len(stand_by_slaves) > 0:
                    inst_list.append(
                        "{}{}{}".format(stand_by_slaves[0].machine.ip, IP_PORT_DIVIDER, stand_by_slaves[0].port)
                    )
                sub_pipeline.add_sub_pipeline(
                    sub_flow=mysql_rollback_data_sub_flow(
                        root_id=self.root_id,
                        ticket_data=copy.deepcopy(self.data),
                        cluster=mycluster,
                        cluster_model=cluster_class,
                        ins_list=inst_list,
                        is_rollback_binlog=True,
                    )
                )

            # 远程备份+时间
            elif self.data["rollback_type"] == RollbackType.REMOTE_AND_TIME.value:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_remote_and_time(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=mycluster
                    )
                )
            # 远程备份+备份ID
            elif self.data["rollback_type"] == RollbackType.REMOTE_AND_BACKUPID.value:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_remote_and_backupid(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=mycluster
                    )
                )

            # 本地备份+备份ID
            elif self.data["rollback_type"] == RollbackType.LOCAL_AND_BACKUPID:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_local_and_backupid(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=mycluster
                    )
                )
            else:
                raise NormalTenDBFlowException(message=_("rollback_type不存在"))

            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("定点恢复")))

        mysql_restore_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_slave_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)

    def rollback_to_cluster_flow(self):
        """
        定义重建slave节点的流程
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [i["cluster_id"] for i in self.ticket_data["infos"]]
        cluster_ids_desc = [i["rollback_cluster_id"] for i in self.ticket_data["infos"]]
        cluster_ids.extend(cluster_ids_desc)
        mysql_restore_slave_pipeline = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )
        #  下发actor
        sub_pipeline_list = []
        for info in self.ticket_data["infos"]:
            self.data = copy.deepcopy(info)
            cluster_class = Cluster.objects.get(id=self.data["cluster_id"])
            master = cluster_class.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
            self.data["bk_biz_id"] = cluster_class.bk_biz_id
            self.data["bk_cloud_id"] = cluster_class.bk_cloud_id
            self.data["db_module_id"] = cluster_class.db_module_id
            self.data["module"] = cluster_class.db_module_id
            self.data["time_zone"] = cluster_class.time_zone
            self.data["created_by"] = self.ticket_data["created_by"]
            self.data["ticket_type"] = self.ticket_data["ticket_type"]
            self.data["cluster_type"] = cluster_class.cluster_type
            self.data["uid"] = self.ticket_data["uid"]
            self.data["city"] = cluster_class.region
            self.data["force"] = info.get("force", False)
            self.data["charset"], self.data["db_version"] = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=self.data["db_module_id"],
                cluster_type=self.data["cluster_type"],
            )

            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))

            rollback_class = Cluster.objects.get(id=self.data["rollback_cluster_id"])
            storages = rollback_class.storageinstance_set.all()
            rollback_pipeline_list = []
            for rollback_storage in storages:
                if not check_storage_database(
                    rollback_class.bk_cloud_id, rollback_storage.machine.ip, rollback_storage.port
                ):
                    logger.error("cluster {} check database fail".format(rollback_class.id))
                    raise NormalSpiderFlowException(
                        message=_("回档集群 {} 空闲检查不通过，请确认回档集群是否存在非系统数据库".format(rollback_class.id))
                    )
                mycluster = {
                    "name": cluster_class.name,
                    "cluster_id": cluster_class.id,
                    "cluster_type": cluster_class.cluster_type,
                    "bk_biz_id": cluster_class.bk_biz_id,
                    "bk_cloud_id": cluster_class.bk_cloud_id,
                    "db_module_id": cluster_class.db_module_id,
                    "databases": self.data["databases"],
                    "tables": self.data["tables"],
                    "databases_ignore": self.data["databases_ignore"],
                    "tables_ignore": self.data["tables_ignore"],
                    "charset": self.data["charset"],
                    "change_master": False,
                    "file_target_path": "/data/dbbak/{}/{}".format(self.root_id, rollback_storage.port),
                    "skip_local_exists": True,
                    "name_regex": "^.+{}\\.\\d+(\\..*)*$".format(master.port),
                    "rollback_time": self.data["rollback_time"],
                    "backupinfo": self.data["backupinfo"],
                    "rollback_type": self.data["rollback_type"],
                    "rollback_ip": rollback_storage.machine.ip,
                    "rollback_port": rollback_storage.port,
                    "backend_port": rollback_storage.port,
                    "master_port": master.port,
                    "master_ip": master.machine.ip,
                }
                exec_act_kwargs = ExecActuatorKwargs(
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    cluster_type=ClusterType.TenDBHA,
                    cluster=mycluster,
                )

                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.mysql_mkdir_dir.__name__
                exec_act_kwargs.exec_ip = rollback_storage.machine.ip
                rollback_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(self.data))
                rollback_pipeline.add_act(
                    act_name=_("下发db-actor到节点"),
                    act_component_code=TransFileComponent.code,
                    kwargs=asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=rollback_storage.machine.bk_cloud_id,
                            exec_ip=[rollback_storage.machine.ip],
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                )
                rollback_pipeline.add_act(
                    act_name=_("创建目录 {}".format(mycluster["file_target_path"])),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(exec_act_kwargs),
                )

                # 本地备份+时间
                if self.data["rollback_type"] == RollbackType.LOCAL_AND_TIME:
                    inst_list = ["{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER, master.port)]
                    stand_by_slaves = cluster_class.storageinstance_set.filter(
                        instance_inner_role=InstanceInnerRole.SLAVE.value,
                        is_stand_by=True,
                        status=InstanceStatus.RUNNING.value,
                    ).exclude(machine__ip__in=[rollback_storage.machine.ip])
                    if len(stand_by_slaves) > 0:
                        inst_list.append(
                            "{}{}{}".format(stand_by_slaves[0].machine.ip, IP_PORT_DIVIDER, stand_by_slaves[0].port)
                        )
                    rollback_pipeline.add_sub_pipeline(
                        sub_flow=mysql_rollback_data_sub_flow(
                            root_id=self.root_id,
                            ticket_data=copy.deepcopy(self.data),
                            cluster=mycluster,
                            cluster_model=cluster_class,
                            ins_list=inst_list,
                            is_rollback_binlog=True,
                        )
                    )

                # 远程备份+时间
                elif self.data["rollback_type"] == RollbackType.REMOTE_AND_TIME.value:
                    rollback_pipeline.add_sub_pipeline(
                        sub_flow=rollback_remote_and_time(
                            root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=mycluster
                        )
                    )
                # 远程备份+备份ID
                elif self.data["rollback_type"] == RollbackType.REMOTE_AND_BACKUPID.value:
                    rollback_pipeline.add_sub_pipeline(
                        sub_flow=rollback_remote_and_backupid(
                            root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=mycluster
                        )
                    )

                # 本地备份+备份ID
                elif self.data["rollback_type"] == RollbackType.LOCAL_AND_BACKUPID:
                    rollback_pipeline.add_sub_pipeline(
                        sub_flow=rollback_local_and_backupid(
                            root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=mycluster
                        )
                    )
                else:
                    raise NormalTenDBFlowException(message=_("rollback_type不存在"))

                rollback_pipeline_list.append(
                    rollback_pipeline.build_sub_process(
                        sub_name=_("定点回档到{}:{}".format(rollback_storage.machine.ip, rollback_storage.port))
                    )
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=rollback_pipeline_list)
            sub_pipeline_list.append(
                sub_pipeline.build_sub_process(sub_name=_("定点回档到{}".format(rollback_class.immute_domain)))
            )
        mysql_restore_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_slave_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext(), is_drop_random_user=True)
