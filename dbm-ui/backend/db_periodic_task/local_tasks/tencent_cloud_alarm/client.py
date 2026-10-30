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
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone

import requests

SERVICE = "monitor"
ACTION = "DescribeAlarmHistories"
VERSION = "2018-07-24"
ALGORITHM = "TC3-HMAC-SHA256"
CONTENT_TYPE = "application/json; charset=utf-8"
DEFAULT_DOMAIN = "monitor.internal.tencentcloudapi.com"
MAX_WINDOW_SECONDS = 8 * 24 * 60 * 60
API_PAGE_LIMIT = 100
CLB_NAMESPACE = "private_lb_client_to_lb_other"
REDIS_NAMESPACE = "redis_mem_edition"
TAG_PAGE_SIZE = 100
TAG_ID_BATCH = 50
TAG_SERVICE = "tag"
TAG_ACTION = "DescribeResourceTagsByResourceIds"
TAG_VERSION = "2018-08-13"


class TencentCloudCredential:
    def __init__(self, secret_id, secret_key, token="", region="ap-guangzhou", domain=DEFAULT_DOMAIN):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.token = token or ""
        self.region = region or "ap-guangzhou"
        self.domain = (domain or DEFAULT_DOMAIN).split("://")[-1].strip("/")


def _hmac_sha256(key, message):
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def authorization(secret_id, secret_key, host, timestamp, payload, service=SERVICE, action=ACTION):
    date = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
    canonical_headers = "content-type:{content_type}\nhost:{host}\nx-tc-action:{action}\n".format(
        content_type=CONTENT_TYPE,
        host=host,
        action=action.lower(),
    )
    signed_headers = "content-type;host;x-tc-action"
    hashed_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    canonical_request = "\n".join(["POST", "/", "", canonical_headers, signed_headers, hashed_payload])
    credential_scope = "{date}/{service}/tc3_request".format(date=date, service=service)
    string_to_sign = "\n".join(
        [
            ALGORITHM,
            str(timestamp),
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = _hmac_sha256(secret_date, service)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    return (
        "{algorithm} Credential={secret_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    ).format(
        algorithm=ALGORITHM,
        secret_id=secret_id,
        credential_scope=credential_scope,
        signed_headers=signed_headers,
        signature=signature,
    )


def response_error(result):
    if not isinstance(result, dict):
        return {"Code": "InvalidResponse", "Message": "response is not an object"}
    return (result.get("Response") or {}).get("Error")


def _post(credential, host, action, version, service, region, body):
    payload = json.dumps(body, separators=(",", ":"))
    timestamp = int(time.time())
    headers = {
        "Authorization": authorization(
            credential.secret_id, credential.secret_key, host, timestamp, payload, service=service, action=action
        ),
        "Content-Type": CONTENT_TYPE,
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": version,
        "X-TC-Region": region,
    }
    if credential.token:
        headers["X-TC-Token"] = credential.token
    try:
        response = requests.post("https://{}/".format(host), data=payload.encode("utf-8"), headers=headers, timeout=30)
    except requests.RequestException:
        return {"Response": {"Error": {"Code": "RequestError", "Message": "request failed"}}}
    try:
        result = response.json()
    except ValueError:
        return {"Response": {"Error": {"Code": "InvalidResponse", "Message": "response is not json"}}}
    if response.status_code >= 400 and not response_error(result):
        return {"Response": {"Error": {"Code": "HTTP{}".format(response.status_code), "Message": "request failed"}}}
    return result


def request_page(credential, start, end, page_number, namespace):
    body = {
        "Module": "monitor",
        "StartTime": start,
        "EndTime": end,
        "Order": "ASC",
        "PageNumber": page_number,
        "PageSize": API_PAGE_LIMIT,
        "MonitorTypes": ["MT_QCE"],
        "Namespaces": [{"MonitorType": "MT_QCE", "Namespace": namespace}],
    }
    return _post(credential, credential.domain, ACTION, VERSION, SERVICE, credential.region, body)


def fetch_alarm_histories(credential, namespace, start, end):
    """拉取一个云监控命名空间的告警历史。失败时返回已取到的记录和错误。"""
    histories = []
    cursor = start
    while cursor < end:
        window_end = min(cursor + MAX_WINDOW_SECONDS, end)
        page_number = 1
        while True:
            result = request_page(credential, cursor, window_end, page_number, namespace)
            error = response_error(result)
            if error:
                return histories, error
            response = result.get("Response") or {}
            total = int(response.get("TotalCount") or 0)
            batch = response.get("Histories") or []
            histories.extend(batch)
            if not batch or page_number * API_PAGE_LIMIT >= total:
                break
            page_number += 1
        cursor = window_end
    return histories, None


def tag_host(monitor_domain):
    if "internal" in (monitor_domain or ""):
        return "tag.internal.tencentcloudapi.com"
    return "tag.tencentcloudapi.com"


def fetch_redis_tags(credential, region, resource_ids):
    """按 Redis 实例 ID 查询标签。调用失败时抛出 RuntimeError。"""
    found = {resource_id: [] for resource_id in resource_ids}
    host = tag_host(credential.domain)
    for offset in range(0, len(resource_ids), TAG_ID_BATCH):
        batch = resource_ids[offset : offset + TAG_ID_BATCH]
        page_offset = 0
        while True:
            result = _post(
                credential,
                host,
                TAG_ACTION,
                TAG_VERSION,
                TAG_SERVICE,
                region,
                {
                    "ServiceType": "redis",
                    "ResourcePrefix": "instance",
                    "ResourceIds": batch,
                    "ResourceRegion": region,
                    "Offset": page_offset,
                    "Limit": TAG_PAGE_SIZE,
                },
            )
            error = response_error(result)
            if error:
                raise RuntimeError("{code} {message}".format(code=error.get("Code"), message=error.get("Message")))
            response = result.get("Response") or {}
            for item in response.get("Tags") or []:
                resource_id = item.get("ResourceId")
                if resource_id not in found:
                    continue
                found[resource_id].append({"键": item.get("TagKey") or "", "值": item.get("TagValue") or ""})
            total = int(response.get("TotalCount") or 0)
            page_offset += TAG_PAGE_SIZE
            if page_offset >= total:
                break
    return found
