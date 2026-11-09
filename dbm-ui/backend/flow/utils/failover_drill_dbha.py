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
import ipaddress
import logging
from typing import List, Optional, Tuple

from backend.components.hadb.client import HADBApi
from backend.components.hadbv2.client import HADBApiV2
from backend.db_periodic_task.constants import FailoverDrillVersion

logger = logging.getLogger("flow")


def query_switch_queue(
    dbha_version: str,
    app: str,
    start_time: str,
    finished_time: str,
    extra_v1_args: Optional[dict] = None,
    timeout: Optional[int] = None,
    retry_times: Optional[int] = None,
) -> Tuple[int, str, list]:
    """
    按 DBHA 版本查询切换队列，返回 (code, msg, data)
    v1 响应外壳为 {code, msg, data}，v2 为 {code, message, data}
    v2 只认 app 与时间范围，其他过滤条件会被忽略
    接口不可用（HTTP 非 200、超时、非 JSON）时抛异常，由调用方处理
    """
    query_args = {
        "app": str(app),
        "switch_start_time": start_time,
        "switch_finished_time": finished_time,
    }
    if dbha_version == FailoverDrillVersion.V2:
        client = HADBApiV2
    else:
        client = HADBApi
        query_args.update(extra_v1_args or {})

    # DataAPI 会把 retry_times 写回模块级单例，调用后恢复，避免影响其它调用方
    api = client.switch_queue
    origin_retry_times = api.max_retry_times
    try:
        resp = api(
            params={"name": "query_switch_queue", "query_args": query_args},
            raw=True,
            timeout=timeout,
            retry_times=retry_times,
        )
    finally:
        api.max_retry_times = origin_retry_times
    msg = resp.get("msg") or resp.get("message") or ""
    return resp.get("code"), msg, resp.get("data") or []


def _extract_service_ips(data: object) -> List[str]:
    if not isinstance(data, dict):
        return []
    candidates = data.get("ips")
    if not isinstance(candidates, list) or not candidates:
        candidates = []
        servers = data.get("servers")
        if isinstance(servers, list):
            for server in servers:
                if isinstance(server, dict) and isinstance(server.get("ips"), list):
                    candidates.extend(server["ips"])
    ips: List[str] = []
    for raw_ip in candidates:
        ip = str(raw_ip or "").strip()
        if not ip:
            continue
        try:
            normalized_ip = str(ipaddress.ip_address(ip))
        except ValueError:
            logger.warning("discard invalid dbha-v2 service ip from ha-servers: %r", raw_ip)
            continue
        if normalized_ip not in ips:
            ips.append(normalized_ip)
    return ips


def get_dbha_v2_service_ips(bk_cloud_id: int, logical_city_id: int) -> List[str]:
    """
    获取需要在演练主机上屏蔽的 dbha-v2 服务 IP。
    meta/ha-servers 返回当前注册中心里的全局 dbha-v2 服务节点列表（admin/analysis/receiver），
    接口本身不支持按云区域或逻辑城市过滤，演练也需要屏蔽全部服务节点 IP；
    bk_cloud_id 与 logical_city_id 仅用于日志排障上下文。
    服务不可用、返回非 0 或无有效 IP 时记录原因并返回空列表；调用方将空列表视为"无法演练"。
    """
    try:
        resp = HADBApiV2.ha_servers(params={}, raw=True)
    except Exception as e:  # pylint: disable=broad-except
        logger.warning(
            "query dbha-v2 ha-servers failed, bk_cloud_id=%s logical_city_id=%s err=%s",
            bk_cloud_id,
            logical_city_id,
            e,
        )
        return []

    if not isinstance(resp, dict):
        logger.warning(
            "dbha-v2 ha-servers returned non-dict response, bk_cloud_id=%s logical_city_id=%s resp=%r",
            bk_cloud_id,
            logical_city_id,
            resp,
        )
        return []

    code = resp.get("code")
    msg = resp.get("msg") or resp.get("message") or ""
    if code != 0:
        logger.warning(
            "dbha-v2 ha-servers returned error, bk_cloud_id=%s logical_city_id=%s code=%s message=%s",
            bk_cloud_id,
            logical_city_id,
            code,
            msg,
        )
        return []

    ips = _extract_service_ips(resp.get("data"))
    if not ips:
        logger.warning(
            "dbha-v2 ha-servers returned empty ips, bk_cloud_id=%s logical_city_id=%s data=%r",
            bk_cloud_id,
            logical_city_id,
            resp.get("data"),
        )
    return ips
