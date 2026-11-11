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
import re

from django.utils.translation import gettext as _

from backend.db_services.dns_domain.constants import (
    DOMAIN_LABEL_MAX_LENGTH,
    DOMAIN_MAX_LENGTH,
    DOMAIN_SUFFIX,
    REMARK_MAX_LENGTH,
)
from backend.db_services.dns_domain.format import normalize_domain
from backend.exceptions import ValidationError

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def validate_domain(domain: str) -> str:
    """校验完整域名。格式由调用方先检查，这里是后端兜底。"""
    normalized = normalize_domain(domain)
    if not normalized.endswith(DOMAIN_SUFFIX):
        raise ValidationError(_("域名必须以 .db 结尾"))
    if len(normalized) > DOMAIN_MAX_LENGTH:
        raise ValidationError(_("域名总长度不能超过 {}").format(DOMAIN_MAX_LENGTH))
    labels = normalized.split(".")
    if any(not label for label in labels):
        raise ValidationError(_("域名格式不正确"))
    for label in labels:
        if len(label) > DOMAIN_LABEL_MAX_LENGTH or not _LABEL_RE.fullmatch(label):
            raise ValidationError(_("域名每段只能是小写字母、数字、连字符，且首尾为字母或数字"))
    return normalized


def validate_ips(ips: list) -> list:
    if not ips:
        raise ValidationError(_("至少填写一个 IP"))
    normalized = []
    seen = set()
    for raw in ips:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        try:
            ipaddress.IPv4Address(text)
        except ipaddress.AddressValueError:
            raise ValidationError(_("IP 格式不正确: {}").format(text))
        seen.add(text)
        normalized.append(text)
    if not normalized:
        raise ValidationError(_("至少填写一个 IP"))
    return normalized


def validate_owners(owners: list) -> list:
    if not isinstance(owners, list):
        raise ValidationError(_("负责人格式不正确"))
    normalized = []
    seen = set()
    for raw in owners:
        name = str(raw or "").strip()
        if not name or name in seen:
            continue
        if len(name) > 64:
            raise ValidationError(_("负责人名称过长"))
        seen.add(name)
        normalized.append(name)
    if not normalized:
        raise ValidationError(_("至少保留 1 名负责人"))
    return normalized


def validate_remark(remark: str) -> str:
    text = "" if remark is None else str(remark).strip()
    if len(text) > REMARK_MAX_LENGTH:
        raise ValidationError(_("备注不能超过 {} 个字符").format(REMARK_MAX_LENGTH))
    return text
