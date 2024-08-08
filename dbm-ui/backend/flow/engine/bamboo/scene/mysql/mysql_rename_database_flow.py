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

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
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
        cluster_ids = [i["cluster_id"] for i in self.data["infos"]]

        cluster_objects = Cluster.objects.filter(id__in=cluster_ids, cluster_type=self.cluster_type)
        machine_group_by_bk_cloud_id = defaultdict(list)
        [
            machine_group_by_bk_cloud_id[cluster_obj.bk_cloud_id].append(
                cluster_obj.main_storage_instances().first().machine.ip
            )
            for cluster_obj in cluster_objects
        ]

        trans_actuator_acts = []
        for k, v in machine_group_by_bk_cloud_id.items():
            trans_actuator_acts.append(
                {
                    "act_name": _("下发actuator介质[云区域ID: {}".format(k)),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=k,
                            exec_ip=list(set(v)),
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                }
            )

        pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids)))
        rename_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        rename_pipeline.add_parallel_acts(acts_list=trans_actuator_acts)

        force = False
        # 按集群聚合rename需求
        merged_jobs = defaultdict(list)
        for ticket_detail_row in self.data["infos"]:
            cluster_id = ticket_detail_row["cluster_id"]
            force = ticket_detail_row["force"]
            merged_jobs[cluster_id].append(
                {"from_database": ticket_detail_row["from_database"], "to_database": ticket_detail_row["to_database"]}
            )

        cluster_pipes = []
        for cluster_id in merged_jobs:
            requests = merged_jobs[cluster_id]  # 这东西是个 List [{from, to}, {from, to}]

            cluster_obj = Cluster.objects.get(
                pk=cluster_id, bk_biz_id=self.data["bk_biz_id"], cluster_type=self.cluster_type
            )
            instance = cluster_obj.main_storage_instances().first()

            cluster_pipe = SubBuilder(
                root_id=self.root_id,
                data={
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ticket_type": self.data["ticket_type"],
                    "requests": requests,
                },
            )

            if not force:
                cluster_pipe.add_act(
                    act_name=_("{} 检查库表是否在用".format(instance.ip_port)),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            run_as_system_user=DBA_SYSTEM_USER,
                            exec_ip=instance.machine.ip,
                            cluster={
                                "ip": instance.machine.ip,
                                "port": instance.port,
                                "dbs": [req["from_database"] for req in requests],
                            },
                            get_mysql_payload_func=MysqlActPayload.rename_check_dbs_in_using.__name__,
                        )
                    ),
                )

            cluster_pipe.add_act(
                act_name=_("{} 执行 rename".format(instance.ip_port)),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        exec_ip=instance.machine.ip,
                        cluster={
                            "ip": instance.machine.ip,
                            "port_shard_id_map": {instance.port: 0},
                        },
                        get_mysql_payload_func=MysqlActPayload.rename_on_mysql.__name__,
                    )
                ),
            )

            cluster_pipes.append(
                cluster_pipe.build_sub_process(sub_name=_("{} 重命名数据库").format(cluster_obj.immute_domain))
            )

        rename_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)

        pipeline.add_sub_pipeline(sub_flow=rename_pipeline.build_sub_process(sub_name=_("DB重命名")))
        logger.info(_("构建重命名数据库流程成功"))
        pipeline.run_pipeline(init_trans_data_class=MySQLTruncateDataContext(), is_drop_random_user=True)
