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
import json
import re
from typing import Optional

_UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_REPORT_ID_RE = re.compile(rf'"report_id"\s*:\s*"({_UUID_RE})"', re.IGNORECASE)
_SHARE_URL_RE = re.compile(rf'(https?://[^\s"\'<>]+/ai-chat/share/{_UUID_RE}/?)', re.IGNORECASE)
_SHARE_UUID_RE = re.compile(rf"/ai-chat/share/({_UUID_RE})/?", re.IGNORECASE)


def _normalize_share_url(share_url: str) -> str:
    """仅校验绝对 URL；不拼接主机、不改写尾斜杠。"""
    url = (share_url or "").strip()
    if not url.startswith(("http://", "https://")):
        return ""
    return url


def _ids_match(report_id: str, share_url: str) -> bool:
    match = _SHARE_UUID_RE.search(share_url or "")
    if not match:
        return False
    return match.group(1).lower() == (report_id or "").lower()


def _from_dict(data: dict) -> Optional[dict]:
    report_id = str(data.get("report_id") or "").strip()
    share_url = _normalize_share_url(str(data.get("share_url") or ""))
    if not report_id or not share_url or not _ids_match(report_id, share_url):
        return None
    summary = data.get("summary")
    return {
        "report_id": report_id,
        "share_url": share_url,
        "summary": "" if summary is None else str(summary),
    }


def parse_config_ai_inspect_res(res: str) -> Optional[dict]:
    """解析 agent 返回，成功需含 report_id 与完整 http(s) share_url，且 UUID 一致。"""
    if not res or not isinstance(res, str):
        return None

    text = res.strip()
    try:
        parsed = _from_dict(json.loads(text))
        if parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    for match in _JSON_FENCE_RE.finditer(text):
        try:
            parsed = _from_dict(json.loads(match.group(1)))
            if parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    report_match = _REPORT_ID_RE.search(text)
    share_match = _SHARE_URL_RE.search(text)
    if not report_match or not share_match:
        return None
    report_id = report_match.group(1)
    share_url = _normalize_share_url(share_match.group(1))
    if not share_url or not _ids_match(report_id, share_url):
        return None
    return {
        "report_id": report_id,
        "share_url": share_url,
        "summary": "",
    }
