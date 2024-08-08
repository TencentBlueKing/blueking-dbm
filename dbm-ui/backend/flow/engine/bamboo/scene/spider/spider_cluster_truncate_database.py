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
from datetime import datetime
from typing import Dict, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceInnerRole, MachineType, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import Cluster, Machine, StorageInstanceTuple
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.generate_drop_stage_db_sql import (
    GenerateDropStageDBSqlComponent,
    GenerateDropStageDBSqlService,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
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
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_ids = [job["cluster_id"] for job in self.data["infos"]]
        dup_cluster_ids = [item for item, count in collections.Counter(cluster_ids).items() if count > 1]
        if dup_cluster_ids:
            raise DBMetaException(message="duplicate clusters found: {}".format(dup_cluster_ids))

        flow_timestr = datetime.now().strftime("%Y%m%d%H%M%S")

        cluster_objects = Cluster.objects.filter(
            id__in=cluster_ids,
            cluster_type=self.cluster_type,
        )

        machine_group_by_bk_cloud_id = collections.defaultdict(list)
        [
            machine_group_by_bk_cloud_id[ele.bk_cloud_id].append(ele.ip)
            for ele in Machine.objects.filter(
                storageinstance__cluster__in=cluster_objects,
                cluster_type=self.cluster_type,
                storageinstance__instance_inner_role=InstanceInnerRole.MASTER.value,
                machine_type=MachineType.REMOTE.value,
            )
        ]
        [
            machine_group_by_bk_cloud_id[ele.bk_cloud_id].append(ele.ip)
            for ele in Machine.objects.filter(
                cluster_type=self.cluster_type,
                machine_type=MachineType.SPIDER.value,
                proxyinstance__cluster__in=cluster_objects,
                proxyinstance__tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
            )
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
        truncate_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        truncate_pipeline.add_parallel_acts(acts_list=trans_actuator_acts)

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
                    "ctl_primary": cluster_obj.tendbcluster_ctl_primary_address(),
                    "flow_timestr": flow_timestr,
                    # 这里的 ip port 只用来需要检查库表使用情况时获取库表列表
                    "ip": cluster_obj.proxyinstance_set.first().machine.ip,
                    "port": cluster_obj.proxyinstance_set.first().port,
                },
            )

            if not job["force"]:
                check_dbs_using_acts = []
                for spider_ins in cluster_obj.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value
                ):
                    check_dbs_using_acts.append(
                        {
                            "act_name": _("{} 检查库表是否在用".format(spider_ins.ip_port)),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(
                                ExecActuatorKwargs(
                                    exec_ip=spider_ins.machine.ip,
                                    bk_cloud_id=cluster_obj.bk_cloud_id,
                                    run_as_system_user=DBA_SYSTEM_USER,
                                    cluster={
                                        "port": spider_ins.port,
                                        "ip": spider_ins.machine.ip,
                                    },
                                    get_mysql_payload_func=MysqlActPayload.truncate_check_dbs_in_using.__name__,
                                )
                            ),
                        }
                    )
                cluster_pipe.add_parallel_acts(acts_list=check_dbs_using_acts)

            cluster_pipe.add_act(
                act_name=_("在中控建立备份库表"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        exec_ip=cluster_obj.tendbcluster_ctl_primary_address().split(IP_PORT_DIVIDER)[0],
                        get_mysql_payload_func=MysqlActPayload.truncate_create_stage_via_ctl.__name__,
                    )
                ),
            )

            # 前面在中控上建立了集群级别的备份库表
            # 所以在 remote 上也有了对应的库表
            # 为了能正常的做 rename table, 需要先 drop stage db
            # 集群的 remote master 按机器聚合
            # {
            #    "1.1.1.1": [{"port": 20000, "shard_id": 0}, {}]
            # }
            remote_master_machine_port_shard_id = collections.defaultdict(dict)
            for remote_master_instance in cluster_obj.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.MASTER.value
            ):
                ip = remote_master_instance.machine.ip
                port = remote_master_instance.port
                shard_id = (
                    StorageInstanceTuple.objects.filter(ejector=remote_master_instance)
                    .first()
                    .tendbclusterstorageset.shard_id
                )
                remote_master_machine_port_shard_id[ip][port] = shard_id

            # 在 remote 上删除备份库
            # 作为独立的流程节点保证幂等
            pre_drop_stage_on_remote_acts = []
            for remote_master_ip in remote_master_machine_port_shard_id:
                pre_drop_stage_on_remote_acts.append(
                    {
                        "act_name": _("{} 预清理备份库".format(remote_master_ip)),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=cluster_obj.bk_cloud_id,
                                run_as_system_user=DBA_SYSTEM_USER,
                                exec_ip=remote_master_ip,
                                cluster={
                                    "port_shard_id_map": remote_master_machine_port_shard_id[remote_master_ip],
                                    "ip": remote_master_ip,
                                },
                                get_mysql_payload_func=MysqlActPayload.truncate_pre_drop_stage_on_remote.__name__,
                            )
                        ),
                    }
                )

            cluster_pipe.add_parallel_acts(acts_list=pre_drop_stage_on_remote_acts)

            # remote 上做常规清档
            # 这个时候 remote 上的备份库是空库
            # 需要做的是
            # 1. rename table to stage
            # 2. 备份触发器, 存储过程, view 到 stage
            truncate_on_remote_acts = []
            for remote_master_ip in remote_master_machine_port_shard_id:
                truncate_on_remote_acts.append(
                    {
                        "act_name": _("{} 执行清档".format(remote_master_ip)),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=cluster_obj.bk_cloud_id,
                                run_as_system_user=DBA_SYSTEM_USER,
                                exec_ip=remote_master_ip,
                                cluster={
                                    "port_shard_id_map": remote_master_machine_port_shard_id[remote_master_ip],
                                    "ip": remote_master_ip,
                                },
                                get_mysql_payload_func=MysqlActPayload.truncate_on_remote.__name__,
                            )
                        ),
                    }
                )

            cluster_pipe.add_parallel_acts(acts_list=truncate_on_remote_acts)

            # 到这里, remote 上
            # 1. 源库中的所有东西都已经备份到 stage 库了
            # 2. 源库中没有表
            # 通过中控以集群基本处理源库, 对清档库根据清档类型处理
            cluster_pipe.add_act(
                act_name=_("在中控执行清档"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=cluster_obj.bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        exec_ip=cluster_obj.tendbcluster_ctl_primary_address().split(IP_PORT_DIVIDER)[0],
                        get_mysql_payload_func=MysqlActPayload.truncate_on_ctl.__name__,
                    )
                ),
                write_payload_var="drop_sqls",
            )

            cluster_pipe.add_act(
                act_name=_("生成删除备份库sql"),
                act_component_code=GenerateDropStageDBSqlComponent.code,
                kwargs={
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                    "cluster_type": cluster_obj.cluster_type,
                    "cluster": cluster_obj.simple_desc,
                    "trans_func": GenerateDropStageDBSqlService.write_drop_sql.__name__,
                },
            )

            cluster_pipes.append(cluster_pipe.build_sub_process(sub_name=_("{} 清档".format(cluster_obj.immute_domain))))

        truncate_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)

        truncate_pipeline.add_act(
            act_name=_("生成删除备份库变更SQL单据"),
            act_component_code=GenerateDropStageDBSqlComponent.code,
            kwargs={"trans_func": GenerateDropStageDBSqlService.generate_dropsql_ticket.__name__},
        )

        pipeline.add_sub_pipeline(sub_flow=truncate_pipeline.build_sub_process(sub_name=_("集群清档")))
        logger.info(_("构造清档流程成功"))
        pipeline.run_pipeline(init_trans_data_class=MySQLTruncateDataContext(), is_drop_random_user=True)
