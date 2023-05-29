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
import logging.config
from typing import Dict, List, Optional, Tuple

from django.utils.translation import ugettext as _

from backend.flow.consts import MongoDBActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.base_subtask import BaseSubTask
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.utils.mongodb import mongodb_password
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs, CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoDBNsFilter, MongoNodeWithLabel, ReplicaSet

logger = logging.getLogger("flow")


# BackupSubTask 处理某个Cluster的备份任务.
class BackupSubTask(BaseSubTask):
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    backup_dir:
    """

    def __init__(self):
        pass

    @classmethod
    def make_kwargs(
        cls, payload: Dict, sub_payload: Dict, rs: ReplicaSet, cluster: MongoDBCluster, file_path: str
    ) -> dict:
        """备份 kwargs"""
        logger.debug("get_backup_node", sub_payload)
        nodes = rs.get_not_backup_nodes()
        if len(nodes) == 0:
            raise Exception("no backup node. rs:{}".format(rs.set_name))
        cls.parse_ns_filter(sub_payload)
        node = nodes[0]

        dba_user = "dba"
        dba_pwd = mongodb_password.MongoDBPassword().get_password_from_db(
            node.ip, int(node.port), node.bk_cloud_id, dba_user
        )["password"]

        ns_filter = sub_payload["ns_filter"]
        is_partial = MongoDBNsFilter.is_partial(ns_filter)
        oplog = payload["oplog"]
        if is_partial and oplog:
            raise Exception(_("oplog为True时, 不支持partial备份"))
        bk_dbm_instance = MongoNodeWithLabel.from_node(node, rs, cluster)
        sudo_account = ActKwargs().get_mongodb_os_conf()["user"]
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": node.bk_cloud_id,
            "exec_ip": node.ip,
            "db_act_template": {
                "action": MongoDBActuatorActionEnum.Backup,
                "file_path": file_path,
                "exec_account": "root",  # 执行脚本的用户，一般是root
                "sudo_account": sudo_account,  # 执行actuator的用户，这里必须是必须用户.
                "payload": {
                    "bk_dbm_instance": bk_dbm_instance.__json__(),
                    "ip": node.ip,
                    "port": int(node.port),
                    "adminUsername": dba_user,
                    "adminPassword": dba_pwd,
                    "skipBackupSysDb": True,
                    "waitBackupSysTaskDone": True,
                    "backupType": "logical",
                    "args": {"backupNode": "", "isPartial": is_partial, "oplog": oplog, "nsFilter": ns_filter},
                },
            },
        }

    @classmethod
    def process_cluster(
        cls,
        root_id: str,
        ticket_data: Optional[Dict],
        sub_ticket_data: Optional[Dict],
        cluster: MongoDBCluster,
        file_path: str,
    ) -> Tuple[SubBuilder, List]:
        """
        backup a ReplicaSet or backup a ShardedCluster
        file_path 为 actuator_workdir 所在的分区MountPoint
        """

        # 创建子流程
        sb = SubBuilder(root_id=root_id, data=ticket_data)
        acts_list = []
        for rs in cluster.get_shards():
            kwargs = cls.make_kwargs(ticket_data, sub_ticket_data, rs, cluster, file_path)
            exec_ip = kwargs["exec_ip"]
            port = kwargs["db_act_template"]["payload"]["port"]
            acts_list.append(
                {
                    "act_name": _("MongoDB-备份-[{}:{}]".format(exec_ip, port)),
                    "act_component_code": ExecJobComponent2.code,
                    "kwargs": kwargs,
                }
            )

        sb.add_parallel_acts(acts_list=acts_list)
        # 将exec_ip取出来。传文件任务需要
        sub_bk_host_list = []
        for v in acts_list:
            sub_bk_host_list.append({"ip": v["kwargs"]["exec_ip"], "bk_cloud_id": v["kwargs"]["bk_cloud_id"]})

        return sb, sub_bk_host_list
