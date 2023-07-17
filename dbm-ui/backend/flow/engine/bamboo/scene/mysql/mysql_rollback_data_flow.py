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
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.consts import RollbackType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_data_sub_flow import (
    install_instance_sub_flow,
    rollback_local_and_backupid,
    rollback_local_and_time,
    rollback_remote_and_backupid,
    rollback_remote_and_time,
    uninstall_instance_sub_flow,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import (
    get_cluster_info,
    get_cluster_ports,
    get_version_and_charset,
)
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
        self.data = data

    def rollback_data_flow(self):
        """
        定义重建slave节点的流程
        """
        mysql_restore_slave_pipeline = Builder(root_id=self.root_id, data=copy.deepcopy(self.data))
        sub_pipeline_list = []
        for info in self.data["infos"]:
            # 根据ip级别安装mysql实例
            cluster_ports = get_cluster_ports([info["cluster_id"]])
            info.update(cluster_ports)
            charset, db_version = get_version_and_charset(
                self.data["bk_biz_id"],
                db_module_id=info["db_module_id"],
                cluster_type=info["cluster_type"],
            )

            ticket_data = copy.deepcopy(self.data)
            ticket_data["clusters"] = info["clusters"]
            ticket_data["mysql_ports"] = info["cluster_ports"]
            ticket_data["charset"] = charset
            ticket_data["db_version"] = db_version

            # 用于兼容 restore slave payload
            info["new_slave_ip"] = info["rollback_ip"]
            info["db_version"] = db_version
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))
            sub_pipeline.add_sub_pipeline(
                sub_flow=install_instance_sub_flow(ticket_data=ticket_data, cluster_info=info)
            )

            one_cluster = get_cluster_info(info["cluster_id"])
            one_cluster["rollback_ip"] = info["rollback_ip"]
            one_cluster["databases"] = info["databases"]
            one_cluster["tables"] = info["tables"]
            one_cluster["databases_ignore"] = info["databases_ignore"]
            one_cluster["tables_ignore"] = info["tables_ignore"]
            one_cluster["backend_port"] = one_cluster["master_port"]
            one_cluster["charset"] = charset
            one_cluster["change_master"] = False
            directory = "/data/dbbak/{}/{}".format(self.root_id, one_cluster["master_port"])
            one_cluster["file_target_path"] = directory
            one_cluster["skip_local_exists"] = True
            one_cluster["name_regex"] = "^.+{}\\.\\d+(\\..*)*$".format(one_cluster["master_port"])
            one_cluster["rollback_time"] = info["rollback_time"]
            # one_cluster["new_master_ip"] = one_cluster["master_ip"]
            # one_cluster["new_slave_ip"] = info["rollback_ip"]
            one_cluster["rollback_ip"] = info["rollback_ip"]
            one_cluster["rollback_port"] = one_cluster["master_port"]
            one_cluster["rollback_time"] = info["rollback_time"]
            one_cluster["backupinfo"] = info["backupinfo"]
            one_cluster["rollback_type"] = info["rollback_type"]

            # 本地备份+时间
            if info["rollback_type"] == RollbackType.LOCAL_AND_TIME:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_local_and_time(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=one_cluster
                    )
                )

            # 远程备份+时间
            elif info["rollback_type"] == RollbackType.REMOTE_AND_TIME.value:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_remote_and_time(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=one_cluster
                    )
                )
            # 远程备份+备份ID
            elif info["rollback_type"] == RollbackType.REMOTE_AND_BACKUPID.value:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_remote_and_backupid(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=one_cluster
                    )
                )

            # 本地备份+备份ID
            elif info["rollback_type"] == RollbackType.LOCAL_AND_BACKUPID:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=rollback_local_and_backupid(
                        root_id=self.root_id, ticket_data=copy.deepcopy(self.data), cluster_info=one_cluster
                    )
                )
            else:
                raise NormalTenDBFlowException(message=_("rollback_type不存在"))

            # 设置暂停。接下来卸载数据库的流程
            sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})
            sub_pipeline.add_sub_pipeline(
                sub_flow=uninstall_instance_sub_flow(ticket_data=ticket_data, cluster_info=one_cluster)
            )
            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("定点恢复")))

        mysql_restore_slave_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_restore_slave_pipeline.run_pipeline(init_trans_data_class=ClusterInfoContext())
