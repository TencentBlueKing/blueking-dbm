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
from typing import Any, Dict, Optional, Union

from backend.db_services.mongodb.autofix.enums import MongoAutofixLogEvent
from backend.db_services.mongodb.autofix.models import MongoAutofixCore, MongoAutofixLog

logger = logging.getLogger("root")


def write_autofix_log(
    event: Union[str, MongoAutofixLogEvent],
    message: str = "",
    *,
    core: Optional[MongoAutofixCore] = None,
    context: Optional[Dict[str, Any]] = None,
    **overrides,
) -> Optional[MongoAutofixLog]:
    """追加一条自愈流水。写库失败只打 warning，不影响主流程。"""
    event_val = event.value if isinstance(event, MongoAutofixLogEvent) else str(event)
    payload: Dict[str, Any] = {
        "core_id": 0,
        "bk_cloud_id": 0,
        "bk_biz_id": 0,
        "cluster_id": 0,
        "immute_domain": "",
        "ip": None,
        "bk_host_id": 0,
        "event": event_val,
        "deal_status": "",
        "confirm_result": "",
        "pre_ticket_id": -1,
        "ticket_id": -1,
        "message": (message or "")[:10000],
        "context": context or {},
        "creator": "system",
        "updater": "system",
    }
    if core is not None:
        payload.update(
            {
                "core_id": core.id or 0,
                "bk_cloud_id": core.bk_cloud_id or 0,
                "bk_biz_id": core.bk_biz_id or 0,
                "cluster_id": core.cluster_id or 0,
                "immute_domain": core.immute_domain or "",
                "ip": core.ip,
                "bk_host_id": core.bk_host_id or 0,
                "deal_status": core.deal_status or "",
                "confirm_result": core.confirm_result or "",
                "pre_ticket_id": core.pre_ticket_id if core.pre_ticket_id is not None else -1,
                "ticket_id": core.ticket_id if core.ticket_id is not None else -1,
            }
        )
    payload.update({k: v for k, v in overrides.items() if v is not None})
    try:
        return MongoAutofixLog.objects.create(**payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning("write_autofix_log fail event=%s err=%s", event_val, exc)
        return None
