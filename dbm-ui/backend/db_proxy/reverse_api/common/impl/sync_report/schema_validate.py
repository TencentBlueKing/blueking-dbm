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
import jsonschema
from jsonschema import validate

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType
from backend.db_proxy.reverse_api.common.impl.sync_report.exceptions import EventValidationException


def events_validate(events):
    schema = {
        "type": "object",
        "properties": {
            "bk_cloud_id": {"type": "integer"},
            "bk_biz_id": {"type": "integer"},
            "cluster_type": {"type": "string", "enum": list(set(ClusterType.get_values()))},
            "event_type": {
                "type": "string",
                "enum": SystemSettings.get_setting_value(SystemSettingsEnum.REVERSE_REPORT_EVENT_TYPES.value) or [],
            },
        },
        "required": ["bk_cloud_id", "bk_biz_id", "cluster_type", "event_type"],
    }

    bad_events = []
    for ev in events:
        try:
            validate(instance=ev, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            bad_events.append({"event": ev, "reason": e.message})

    if bad_events:
        raise EventValidationException(errors=bad_events)
