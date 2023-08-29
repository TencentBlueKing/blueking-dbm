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
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.flow.consts import TruncateDataTypeEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.filter_database_table_by_flashback_input import (
    FilterDatabaseTableFromFlashbackInputComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.check_cluster_table_using_sub import (
    build_check_cluster_table_using_sub_flow,
)
from backend.flow.utils.mysql.mysql_act_dataclass import BKCloudIdKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLFlashBackContext

logger = logging.getLogger("flow")


class TenDBClusterFlashbackFlow(object):
    """
    tendbcluster flashback
    在各remote instance 并发执行
    """

    def __init__(self, root_id: str, cluster_type: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data
        self.cluster_type = cluster_type

    def flashback(self):
        """
        {
            "uid": "{}".format(datetime.now().strftime("%Y%m%d%H%M%f")),
            "created_by": "xxx",
            "bk_biz_id": "3",
            "module": 1,
            "ticket_type": constants.TicketType.TENDB_CLUSTER_FLASHBACK.value,
            "infos": [
                {
                    "cluster_id": cluster_id,
                    "start_time": "2023-07-03 15:06:00",
                    "end_time": "2023-07-03 15:28:00",
                    "databases": ["db_ob1"],
                    "databases_ignore": [],
                    "tables": [],
                    "tables_ignore": [],
                    "force": bool,
                }
            ]
        }
        目前库表输入和库表选择器的逻辑不一样
        这里 tables 为空时指代所有表
        end_time >= start_time
        回档时从 end_time 向 start_time 反演 binlog
        所以
        start_time 是平时说的需要回档到的时间点
        """
        flashback_pipeline = Builder(root_id=self.root_id, data=self.data)
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
                    **deepcopy(job),
                    "uid": self.data["uid"],
                    "created_by": self.data["created_by"],
                    "bk_biz_id": self.data["bk_biz_id"],
                    "ip": cluster_obj.proxyinstance_set.filter(
                        tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                    )
                    .first()
                    .machine.ip,
                    "port": cluster_obj.proxyinstance_set.first().port,
                    "truncate_data_type": TruncateDataTypeEnum.TRUNCATE_TABLE.value,  # 不是真的要删表, 只是复用打开检查必须
                },
            )

            cluster_pipe.add_act(
                act_name=_("获取回档库表"),
                act_component_code=FilterDatabaseTableFromFlashbackInputComponent.code,
                kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
            )

            # 在所有 spider 做库表打开检查
            # 不做连接检查, 因为意义不大
            # 有个问题是, 如何减少因为监控导致的误报呢? 可以考虑多检查一次
            if not self.data["force"]:
                cluster_pipe.add_sub_pipeline(
                    build_check_cluster_table_using_sub_flow(
                        root_id=self.root_id, cluster_obj=cluster_obj, parent_global_data=self.data
                    )
                )

            ip_port_map = defaultdict(list)
            for remote_master_instance in cluster_obj.storageinstance_set.filter(
                instance_inner_role=InstanceInnerRole.MASTER.value
            ):
                ip_port_map[remote_master_instance.machine.ip].append(remote_master_instance.port)

            on_remote_pipes = []
            for ip, port_list in ip_port_map.items():
                on_remote_pipe = SubBuilder(
                    root_id=self.root_id,
                    data={
                        **deepcopy(job),
                        "uid": self.data["uid"],
                        "created_by": self.data["created_by"],
                        "bk_biz_id": self.data["bk_biz_id"],
                    },
                )

                on_remote_pipe.add_act(
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

                port_acts = []
                for port in port_list:
                    shard_id = (
                        StorageInstanceTuple.objects.filter(ejector__machine__ip=ip, ejector__port=port)
                        .first()
                        .tendbclusterstorageset.shard_id
                    )
                    port_job = deepcopy(job)
                    port_job["shard_id"] = shard_id
                    port_job["master_port"] = port
                    port_job["work_dir"] = "/data/dbbak/{}/{}".format(self.root_id, port)

                    port_acts.append(
                        {
                            "act_name": _("端口 {} 执行闪回".format(port)),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(
                                ExecActuatorKwargs(
                                    exec_ip=ip,
                                    bk_cloud_id=cluster_obj.bk_cloud_id,
                                    cluster=port_job,
                                    get_mysql_payload_func=MysqlActPayload.get_spider_flashback_payload.__name__,
                                )
                            ),
                        }
                    )

                on_remote_pipe.add_parallel_acts(port_acts)

                on_remote_pipes.append(on_remote_pipe.build_sub_process(sub_name=_("{} 闪回".format(ip))))

            cluster_pipe.add_parallel_sub_pipeline(sub_flow_list=on_remote_pipes)
            cluster_pipes.append(
                cluster_pipe.build_sub_process(sub_name=_("{} flashback".format(cluster_obj.immute_domain)))
            )

        flashback_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        logger.info(_("构造flashback流程成功"))
        flashback_pipeline.run_pipeline(init_trans_data_class=MySQLFlashBackContext())
