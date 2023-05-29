"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.db.transaction import atomic
from pipeline.component_framework.component import Component

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.models import Ticket


class LinkTBinlogDumperSwitchService(BaseService):
    """
    联动TBinlogDumper 迁移部署单据，写ticket
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")
        get_switch_binlog_info = kwargs["get_binlog_info"]

        # 获取与集群相关联TBinlogDumper实例
        switch_instances = []
        nodes = ExtraProcessInstance.objects.filter(cluster_id=kwargs["cluster_id"], phase=ClusterPhase.ONLINE.value)
        for node in nodes:
            if node.ip == kwargs["target_ip"]:
                # 如果当前实例主机位置与待迁移位置一致，则不作为这次迁移对象
                continue
            switch_binlog_info = getattr(trans_data, get_switch_binlog_info)
            switch_info = {
                "host": node.ip,
                "port": node.listen_port,
                "repl_binlog_file": switch_binlog_info["bin_file"],
                "repl_binlog_pos": switch_binlog_info["bin_position"],
            }
            self.log_info(f"link TBinlogDumper instance info : {switch_info}")
            switch_instances.append(switch_info)

        cluster_switch_info = {"cluster_id": kwargs["cluster_id"], "switch_instances": switch_instances}

        if len(switch_instances) == 0:
            self.log_info(f"There are no nodes that require linkage switching in the cluster [{kwargs['cluster_id']}]")
            return True

        # 保证原子性更新，避免并发时丢失数据
        with atomic():
            ticket = Ticket.objects.select_for_update().get(id=global_data["uid"])
            switch_infos = ticket.details.get("switch_infos", [])
            switch_infos.append(cluster_switch_info)
            ticket.update_details(switch_infos=switch_infos)
            ticket.save()
        return True


class LinkTBinlogDumperSwitchComponent(Component):
    name = __name__
    code = "link_tbinlogdumper_switch"
    bound_service = LinkTBinlogDumperSwitchService
