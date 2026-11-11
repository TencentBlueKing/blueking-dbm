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
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.configuration.constants import PLAT_BIZ_ID
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_services.dns_domain.audit import client_ip_from_request, record_mapping_change
from backend.db_services.dns_domain.constants import (
    AUDIT_OP_TYPE,
    AUDIT_SCOPE_DOMAIN,
    AUDIT_SCOPE_GLOBAL,
    DOMAIN_TYPE_CLUSTER,
    DOMAIN_TYPE_SELF,
    OP_TYPE_ACTION,
    AuditAction,
    MaintainType,
)
from backend.db_services.dns_domain.dns_client import DnsDomainClient
from backend.db_services.dns_domain.format import normalize_domain
from backend.db_services.dns_domain.validators import validate_domain, validate_ips, validate_owners, validate_remark
from backend.exceptions import ValidationError
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.signal import post_save_grant_iam

logger = logging.getLogger("root")


class DnsDomainHandler(object):
    def __init__(self, username: str, request=None):
        """记录当前操作人和请求。"""
        self.username = username
        self.request = request

    def list_domains(self, params: Dict) -> Dict:
        """按检索条件向 DNS 服务要一页域名记录。权限字段由视图装饰器写入。"""
        domain_name = (params.get("domain") or "").strip()
        domain_type = self._search_domain_type(params.get("maintain_type"))
        manager = self._search_manager(params)
        if manager is False:
            return {"count": 0, "results": []}
        limit = params.get("limit")
        offset = params.get("offset") or 0
        client = self._client(PLAT_BIZ_ID, DEFAULT_BK_CLOUD_ID)
        page_size = min(int(limit), 1000)
        page = offset // page_size + 1 if page_size else 1
        data = client.search_domains(domain_name, domain_type, manager or "", page, page_size)
        records, total = data["detail"], data["rowsNum"]
        return {"count": total, "results": [self._search_item(record) for record in records]}

    def retrieve_domain(self, domain: str) -> Dict:
        """用传入的域名向 DNS 检索这一条，再取解析 IP。"""
        record = self._domain_record(normalize_domain(domain))
        if not record:
            raise ValidationError(_("域名不存在"))
        item = self._search_item(record)
        cloud_id = item["bk_cloud_id"]
        if cloud_id in (None, ""):
            cloud_id = DEFAULT_BK_CLOUD_ID
        item["bk_cloud_id"] = int(cloud_id)
        item["ips"] = self._client(PLAT_BIZ_ID, item["bk_cloud_id"]).list_ips(item["domain"])
        item["readonly_reason"] = ""
        if item["maintain_type"] == MaintainType.CLUSTER.value:
            item["readonly_reason"] = _("该域名由集群托管，请在对应集群中操作")
        return item

    def create_domain(self, params: Dict) -> Dict:
        """新建自主维护域名。解析、负责人和备注写入 DNS 服务。"""
        domain = validate_domain(params["domain"])
        ips = validate_ips(params["ips"])
        owners = validate_owners(params.get("owners") or [self.username])
        remark = validate_remark(params.get("remark") or "")
        bk_cloud_id = params.get("bk_cloud_id", DEFAULT_BK_CLOUD_ID)
        self._reject_if_exists(domain, bk_cloud_id)
        client = self._client(PLAT_BIZ_ID, bk_cloud_id)
        client.create_ips(domain, ips, manager=self._join(owners), remark=remark)
        try:
            self._write_log(domain, AuditAction.CREATE.value, self._self_lines(ips, owners, remark))
            self._grant_creator(domain)
        except Exception:
            logger.exception("create dns domain meta failed, rollback dns, domain=%s", domain)
            try:
                client.delete_domain(domain)
            except Exception:  # pylint: disable=broad-except
                logger.exception("rollback dns domain failed, domain=%s", domain)
            raise
        return self.retrieve_domain(domain)

    def check_duplicate(self, params: Dict) -> Dict:
        """校验域名是否已被集群托管或 DNS 服务占用。"""
        domain = validate_domain(params["domain"])
        bk_cloud_id = params.get("bk_cloud_id", DEFAULT_BK_CLOUD_ID)
        return {"domain": domain, "duplicated": self._domain_exists(domain, bk_cloud_id)}

    def update_domain(self, params: Dict) -> Dict:
        """更新自主维护域名的 IP。已有记录走 DNS 更新接口。"""
        domain = normalize_domain(params["domain"])
        client = self._self_client(domain)
        ips = validate_ips(params["ips"])
        owners = validate_owners(params["owners"])
        remark = validate_remark(params.get("remark") or "")
        added, removed = client.replace_ips(domain, ips)
        logs = []
        if added or removed:
            lines = []
            if added:
                lines.append(_("新增 IP: {}").format(self._join(added)))
            if removed:
                lines.append(_("删除 IP: {}").format(self._join(removed)))
            logs.append((AuditAction.UPDATE_IP.value, lines))
        current = self._domain_record(domain)
        old_remark = current.get("remark") or ""
        old_owners = self._record_owners(current)
        if remark != old_remark:
            logs.append((AuditAction.UPDATE_REMARK.value, [_("备注: {} → {}").format(old_remark or "-", remark or "-")]))
        if owners != old_owners:
            logs.append(
                (
                    AuditAction.UPDATE_OWNER.value,
                    [_("负责人: {} → {}").format(self._join(old_owners), self._join(owners))],
                )
            )
        for action, lines in logs:
            self._write_log(domain, action, lines)
        return self.retrieve_domain(domain)

    def delete_domain(self, params: Dict) -> Dict:
        """确认域名后删除 DNS 解析。"""
        domain = normalize_domain(params["domain"])
        confirm_domain = normalize_domain(params["confirm_domain"])
        if confirm_domain != domain:
            raise ValidationError(_("请输入完整域名确认删除"))
        client = self._self_client(domain)
        ips = client.list_ips(domain)
        client.delete_domain(domain)
        self._write_log(domain, AuditAction.DELETE.value, self._self_lines(ips))
        return {"domain": domain}

    def list_audits(self, params: Dict) -> Dict:
        """按筛选条件向 DNS 服务要一页操作日志。"""
        records, total = self._query_oplogs(params, fetch_all=params.get("limit") in (None, -1))
        return {"count": total, "results": [self._audit_dict(item) for item in records]}

    def export_audits(self, params: Dict):
        """按当前筛选条件导出操作日志。"""
        from backend.utils.excel import ExcelHandler

        scope = params["scope"]
        records, __ = self._query_oplogs(params, fetch_all=True)
        rows = [self._audit_dict(item) for item in records]
        for row in rows:
            row["change_content"] = "\n".join(row["change_lines"])
        headers = [
            {"id": "create_at", "name": _("时间")},
            {"id": "operator", "name": _("操作人")},
            {"id": "client_ip", "name": _("客户端 IP")},
            {"id": "action_display", "name": _("操作类型")},
        ]
        if scope == AUDIT_SCOPE_GLOBAL:
            headers.append({"id": "domain", "name": _("域名")})
        headers.append({"id": "change_content", "name": _("变更内容")})
        workbook = ExcelHandler.serialize(rows, headers=headers, match_header=True)
        today = timezone.localdate().strftime("%Y%m%d")
        if scope == AUDIT_SCOPE_GLOBAL:
            filename = _("域名服务-全局操作日志-{}.xlsx").format(today)
        else:
            filename = _("域名服务-{}-操作日志-{}.xlsx").format(params["domain"], today)
        return ExcelHandler.response(workbook, filename)

    def _search_domain_type(self, maintain_type: str):
        """维护方式转成 DNS 检索的 domain_type。不筛选时不传。"""
        if maintain_type == MaintainType.CLUSTER.value:
            return DOMAIN_TYPE_CLUSTER
        if maintain_type == MaintainType.SELF.value:
            return DOMAIN_TYPE_SELF
        return None

    def _search_manager(self, params: Dict):
        """负责人精确匹配。只看我的和指定负责人冲突时返回 False。"""
        owner = (params.get("owner") or "").strip()
        if params.get("mine"):
            if owner and owner != self.username:
                return False
            return self.username
        return owner

    def _search_item(self, record: Dict) -> Dict:
        """把一条 DNS 检索记录转成列表字段。"""
        domain = normalize_domain(record.get("domain_name") or record.get("domain") or "")
        maintain_type, maintain_display = self._maintain_from_domain_type(record.get("domain_type"))
        manager = str(record.get("manager") or "").strip()
        owners = [name.strip() for name in manager.replace("，", ",").split(",") if name.strip()]
        bk_cloud_id = record.get("bk_cloud_id")
        if bk_cloud_id is None:
            bk_cloud_id = DEFAULT_BK_CLOUD_ID
        return {
            "domain": domain,
            "maintain_type": maintain_type,
            "maintain_type_display": maintain_display,
            "owners": owners,
            "remark": record.get("remark") or "",
            "bk_biz_id": PLAT_BIZ_ID,
            "bk_cloud_id": bk_cloud_id,
            "cluster_id": None,
            "updater": "",
            "update_at": self._format_dns_time(record.get("last_change_time")),
            "create_at": self._format_dns_time(record.get("start_time")),
        }

    @staticmethod
    def _maintain_from_domain_type(domain_type):
        try:
            value = int(domain_type)
        except (TypeError, ValueError):
            value = None
        if value == DOMAIN_TYPE_CLUSTER:
            maintain_type = MaintainType.CLUSTER.value
        elif value == DOMAIN_TYPE_SELF:
            maintain_type = MaintainType.SELF.value
        else:
            maintain_type = "" if value is None else str(value)
            return maintain_type, maintain_type
        return maintain_type, str(MaintainType.get_choice_label(maintain_type))

    def _self_client(self, domain: str) -> DnsDomainClient:
        """自主维护域名只认 DNS 服务。集群托管域名直接拒绝。"""
        if self._find_cluster(domain) is not None:
            raise ValidationError(_("该域名由集群托管，请在对应集群中操作"))
        client = self._client(PLAT_BIZ_ID, self._self_cloud_id(domain))
        if not client.has_mapping(domain):
            raise ValidationError(_("域名不存在"))
        return client

    def _self_cloud_id(self, domain: str) -> int:
        cloud_id = self._domain_record(domain).get("bk_cloud_id")
        if cloud_id in (None, ""):
            return DEFAULT_BK_CLOUD_ID
        return int(cloud_id)

    def _domain_record(self, domain: str) -> Dict:
        """按域名取一条 DNS 记录，用来读负责人、备注和云区域。"""
        target = normalize_domain(domain)
        data = self._client(PLAT_BIZ_ID, DEFAULT_BK_CLOUD_ID).search_domains(domain_name=target, page=1, page_size=50)
        for record in data.get("detail") or []:
            if normalize_domain(record.get("domain_name") or "") == target:
                return record
        return {}

    @staticmethod
    def _record_owners(record: Dict) -> List[str]:
        manager = str(record.get("manager") or "").strip()
        return [name.strip() for name in manager.replace("，", ",").split(",") if name.strip()]

    def _grant_creator(self, domain: str):
        """创建成功后给创建人授予该域名的管理权限。"""
        post_save_grant_iam(
            ResourceEnum.DNS_DOMAIN,
            None,
            SimpleNamespace(domain=domain, creator=self.username),
            self.username,
            True,
        )

    def _reject_if_exists(self, domain: str, bk_cloud_id: int):
        """域名已在集群或 DNS 服务中存在时拒绝创建。"""
        if self._domain_exists(domain, bk_cloud_id):
            raise ValidationError(_("域名已存在"))

    def _domain_exists(self, domain: str, bk_cloud_id: int) -> bool:
        """集群入口或 DNS 服务任一占用即视为重复。"""
        if self._find_cluster(domain) is not None:
            return True
        return self._client(PLAT_BIZ_ID, bk_cloud_id).has_mapping(domain)

    def _find_cluster(self, domain: str):
        """按主域名或 DNS 入口查找托管集群。"""
        cluster = Cluster.objects.filter(immute_domain__iexact=domain).first()
        if cluster is not None:
            return cluster
        return (
            ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value)
            .filter(Q(entry__iexact=domain) | Q(entry__iexact=f"{domain}."))
            .select_related("cluster")
            .first()
        )

    @staticmethod
    def _format_time(value) -> str:
        """把时间格式化成本地时间字符串。"""
        if not value:
            return ""
        return timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _format_dns_time(cls, value) -> str:
        if not value:
            return ""
        if hasattr(value, "strftime"):
            return cls._format_time(value)
        text = str(value)
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
        if timezone.is_naive(parsed):
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        return timezone.localtime(parsed).strftime("%Y-%m-%d %H:%M:%S")

    def _query_oplogs(self, params: Dict, fetch_all: bool):
        """带域名时查 /oplog/domain，否则查 /oplog/all。"""
        scope, domain_name, operator = self._oplog_filters(params)
        op_type = AUDIT_OP_TYPE.get(params.get("action") or "", "")
        start_time = params.get("start_time") or ""
        end_time = params.get("end_time") or ""
        client = self._client(PLAT_BIZ_ID, DEFAULT_BK_CLOUD_ID)
        if fetch_all:
            return self._search_all_oplogs(client, scope, domain_name, operator, op_type, start_time, end_time)
        limit = params.get("limit") or 20
        offset = params.get("offset") or 0
        page_size = min(int(limit), 1000)
        page = offset // page_size + 1 if page_size else 1
        data = client.search_oplogs(scope, domain_name, operator, op_type, start_time, end_time, page, page_size)
        return data["detail"], data["rowsNum"]

    def _oplog_filters(self, params: Dict):
        """有域名就走域名日志接口，domain_name 精确匹配。本域关键字按操作人查。"""
        keyword = (params.get("keyword") or "").strip()
        operator = (params.get("operator") or "").strip()
        domain = normalize_domain(params.get("domain") or "")
        if params["scope"] == AUDIT_SCOPE_DOMAIN:
            return AUDIT_SCOPE_DOMAIN, domain, operator or keyword
        domain_name = domain or normalize_domain(keyword)
        if domain_name:
            return AUDIT_SCOPE_DOMAIN, domain_name, operator
        return AUDIT_SCOPE_GLOBAL, "", operator

    def _search_all_oplogs(self, client, scope, domain_name, operator, op_type, start_time, end_time):
        """导出时按 DNS 分页把日志取完。"""
        page = 1
        page_size = 1000
        records = []
        total = 0
        while True:
            data = client.search_oplogs(scope, domain_name, operator, op_type, start_time, end_time, page, page_size)
            detail = data["detail"]
            total = data["rowsNum"]
            records.extend(detail)
            if not detail or len(records) >= total:
                break
            page += 1
        return records, total

    def _audit_dict(self, item: Dict) -> Dict:
        """把一条 DNS 日志转成接口字段。"""
        op_type = item.get("op_type") or ""
        action = OP_TYPE_ACTION.get(op_type, "")
        if action:
            action_display = str(AuditAction.get_choice_label(action))
        else:
            action = op_type
            action_display = op_type
        content = item.get("content") or ""
        lines = [line for line in str(content).split("\n") if line]
        return {
            "id": item.get("uid") or item.get("id") or 0,
            "domain": normalize_domain(item.get("domain_name") or ""),
            "operator": item.get("operator") or "",
            "client_ip": item.get("client_ip") or "",
            "action": action,
            "action_display": action_display,
            "change_lines": lines,
            "create_at": self._format_dns_time(item.get("op_time")),
        }

    def _self_lines(self, ips, owners=None, remark=None) -> List[str]:
        """组装自主维护域名的日志内容。"""
        lines = [
            _("IP 集合: {}").format(self._join(ips)),
            _("维护方式: {}").format(MaintainType.get_choice_label(MaintainType.SELF.value)),
        ]
        if owners is not None:
            lines.append(_("负责人: {}").format(self._join(owners)))
        if remark is not None:
            lines.append(_("备注: {}").format(remark or "-"))
        return lines

    def _write_log(self, domain: str, action: str, lines: List[str]):
        """写入一条域名操作日志。"""
        operator, client_ip = self.username, client_ip_from_request(self.request)
        record_mapping_change(domain, action, lines, operator=operator, client_ip=client_ip)

    @staticmethod
    def _client(bk_biz_id: int, bk_cloud_id: int) -> DnsDomainClient:
        """按业务和云区域构造 DNS 客户端。"""
        return DnsDomainClient(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id)

    @staticmethod
    def _join(values) -> str:
        """把列表拼成日志里的展示文本。"""
        values = [str(value) for value in values or [] if str(value)]
        return ", ".join(values) if values else "-"
