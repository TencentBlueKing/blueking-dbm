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

from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.models import StateType
from backend.tests.mock_data import constant
from backend.ticket.constants import TicketType

PASSWORD = "xxxxxxxxxx"
ROOT_ID = "a884b5422f7111ed830cc2afcf9e926b"
BK_USERNAME = "admin"
SN = "NO2019090519542603"
BK_BIZ_ID = constant.BK_BIZ_ID

DB_MODULE_DATA = {
    "creator": "admin",
    "create_at": "2022-07-28 07:09:46",
    "updater": "admin",
    "update_at": "2022-07-29 07:09:46",
    "bk_biz_id": constant.BK_BIZ_ID,
    "db_module_name": "blueking-module",
    "db_module_id": 1,
    "cluster_type": ClusterType.TenDBSingle,
    "alias_name": "",
}

FLOW_TREE_DATA = {
    "bk_biz_id": constant.BK_BIZ_ID,
    "uid": "REQ20200831000005",
    "ticket_type": TicketType.MYSQL_SINGLE_APPLY.name,
    "root_id": ROOT_ID,
    "tree": {"activities": {"SQL_IMPORT_NODE_ID": {"component": {"code": 1}}}},
    "status": StateType.FINISHED.value,
    "created_by": BK_USERNAME,
    "created_at": "2022-07-28 07:09:46",
    "updated_at": "2022-07-29 07:09:46",
}

TICKET_DATA = {
    "id": 585,
    "create_at": "2025-06-28 09:05:48",
    "update_at": "2025-06-28 10:05:48",
    "bk_biz_id": constant.BK_BIZ_ID,
    "ticket_type": "TENDBCLUSTER_SPIDER_SWITCH_NODES",
    "group": "tendbcluster",
    "status": "TODO",
    "remark": "",
    "details": {},
    "send_msg_config": "",
}

FLOW_DATA = [
    {
        "id": 844,
        "flow_type": "BK_ITSM",
        "flow_obj_id": "REQ20250703000001",
        "details": {},
        "status": "SUCCEEDED",
        "context": {"ack": True},
    },
    {
        "id": 845,
        "flow_type": "PAUSE",
        "flow_obj_id": "pause_03cbb99657d811f098cdba0400c0704d",
        "details": {},
        "status": "RUNNING",
        "context": {"ack": True},
    },
    {
        "id": 846,
        "flow_type": "RESOURCE_BATCH_APPLY",
        "flow_obj_id": "",
        "details": {},
        "status": "PENDING",
        "context": {"ack": True},
    },
    {
        "id": 847,
        "flow_type": "INNER_FLOW",
        "flow_obj_id": "",
        "details": {},
        "status": "PENDING",
        "context": {"ack": True},
    },
]

TODO_DATA = [
    {
        "id": 521,
        "name": "【TenDB Cluster 替换接入层】单据等待审批",
        "type": "ITSM",
        "status": "DONE_SUCCESS",
    },
    {
        "id": 522,
        "name": "【TenDB Cluster 替换接入层】流程待确认，是否继续？",
        "type": "APPROVE",
        "status": "TODO",
    },
]

TICKET_CONFIG_DATA = {
    "need_itsm": True,
    "expire_config": {
        "pause": 1,
        "timer": 1,
        "itsm_expire": 1,
        "flow_todo_expire": 1,
        "inner_flow_expire": 1,
        "resource_replenish": 1,
    },
    "need_manual_confirm": True,
}
