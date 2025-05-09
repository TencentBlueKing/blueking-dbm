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
from backend import env
from backend.configuration.models import SystemSettings


def mysql_crond_config(bk_cloud_id: int, ip: str) -> dict:
    bkm_dbm_report = SystemSettings.get_setting_value(key="BKM_DBM_REPORT")
    event_data_id = bkm_dbm_report["event"]["data_id"]
    event_data_token = bkm_dbm_report["event"]["token"]
    metrics_data_id = bkm_dbm_report["metric"]["data_id"]
    metrics_data_token = bkm_dbm_report["metric"]["token"]

    return {
        "ip": ip,
        "bk_cloud_id": bk_cloud_id,
        "event_data_id": int(event_data_id),
        "event_data_token": event_data_token,
        "metrics_data_id": int(metrics_data_id),
        "metrics_data_token": metrics_data_token,
        "beat_path": env.MYSQL_CROND_BEAT_PATH,
        "agent_address": env.MYSQL_CROND_AGENT_ADDRESS,
    }
