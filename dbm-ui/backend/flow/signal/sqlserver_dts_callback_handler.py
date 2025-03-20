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

from backend.db_meta.models.sqlserver_dts import DtsStatus, SqlserverDtsInfo
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.signal.callback_map import create_ticket_handler
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


flow_full_migrate_map = {
    StateType.FAILED: DtsStatus.FullFailed,
    StateType.REVOKED: DtsStatus.FullFailed,
    StateType.RUNNING: DtsStatus.FullOnline,
    StateType.READY: DtsStatus.ToDo,
    StateType.CREATED: DtsStatus.ToDo,
}

flow_incr_migrate_map = {
    StateType.FAILED: DtsStatus.IncrFailed,
    StateType.REVOKED: DtsStatus.IncrFailed,
    StateType.RUNNING: DtsStatus.IncrOnline,
    StateType.READY: DtsStatus.ToDo,
    StateType.CREATED: DtsStatus.ToDo,
}


@create_ticket_handler(TicketType.SQLSERVER_FULL_MIGRATE)
def sqlserver_dts_callback_handler(root_id: str, node_id: str, status: StateType, **kwargs):
    """
    通用的信号状态处理单据状态的方法，不满足于sqlserver的dts单据，无法维护到dts任务信息的状态
    这里针对sqlserver_dts单据，不同单据状态变更对应的dts信息的状态信息，以此达到状态一致性
    具体逻辑：通过node_id获取当前component所在的子流程，捕捉到对应的dts_id，变更状态
    """
    logger.info("exec sqlserver_dts_callback_handler")
    engine = BambooEngine(root_id=root_id)
    data_inputs = engine.get_node_input_data(node_id=node_id).data
    if data_inputs.get("global_data", {}).get("dts_id") and flow_full_migrate_map.get(status):
        dts_id = data_inputs.get("global_data").get("dts_id")
        SqlserverDtsInfo.objects.filter(id=dts_id).update(status=flow_full_migrate_map[status])
    return


@create_ticket_handler(TicketType.SQLSERVER_INCR_MIGRATE)
def sqlserver_dts_incr_callback_handler(root_id: str, node_id: str, status: StateType, **kwargs):
    logger.info("exec sqlserver_dts_incr_callback_handler")
    engine = BambooEngine(root_id=root_id)
    data_inputs = engine.get_node_input_data(node_id=node_id).data
    if data_inputs.get("global_data", {}).get("dts_id") and flow_incr_migrate_map.get(status):
        dts_id = data_inputs.get("global_data").get("dts_id")
        SqlserverDtsInfo.objects.filter(id=dts_id).update(status=flow_incr_migrate_map[status])
    return
