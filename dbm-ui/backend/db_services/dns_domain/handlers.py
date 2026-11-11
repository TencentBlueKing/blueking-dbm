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
from typing import Dict, List

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.configuration.constants import PLAT_BIZ_ID
from backend.configuration.models import DBAdministrator
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_services.dns_domain.audit import client_ip_from_request, record_mapping_change
from backend.db_services.dns_domain.constants import AUDIT_SCOPE_DOMAIN, AUDIT_SCOPE_GLOBAL, AuditAction, MaintainType
from backend.db_services.dns_domain.dns_client import DnsDomainClient
from backend.db_services.dns_domain.format import normalize_domain
from backend.db_services.dns_domain.models import DnsDomain, DnsDomainAuditLog
from backend.db_services.dns_domain.validators import validate_domain, validate_ips, validate_owners, validate_remark
from backend.exceptions import ValidationError
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.permission import Permission

logger = logging.getLogger("root")


class DnsDomainHandler(object):
    def __init__(self, username: str, request=None):
        """记录当前操作人和请求。"""
        self.username = username
        self.request = request

    def list_domains(self, params: Dict) -> Dict:
        """合并两类域名并过滤分页。无权限的入口置灰，点击打开 IAM 申请弹窗。"""
        items = self._collect_domains()
        items = self._filter_domains(items, params)
        items.sort(key=lambda item: item["domain"])
        total = len(items)
        offset = params.get("offset") or 0
        limit = params.get("limit")
        page = items if limit in (None, -1) else items[offset : offset + limit]
        allowed = self._manageable_domains([item["domain"] for item in page])
        for item in page:
            manageable = item["domain"] in allowed
            # 无 dns_manage 时域名、编辑、删除置灰。集群托管另有只读限制，不走这把锁。
            item["permission"] = {ActionEnum.DNS_MANAGE.id: manageable}
            item["has_dns_manage"] = manageable
            item["editable"] = manageable and item["maintain_type"] == MaintainType.SELF.value
            item["deletable"] = item["editable"]
        permission = self._permission()
        can_create = permission.is_allowed(ActionEnum.DNS_DOMAIN_CREATE, [])
        can_view_global_audit = permission.is_allowed(ActionEnum.DNS_AUDIT_VIEW, [])
        return {
            "count": total,
            "results": page,
            # false 时入口置灰。点击后由对应接口返回 IAM 无权限数据，前端打开申请弹窗。
            "can_create": can_create,
            "can_view_global_audit": can_view_global_audit,
            "permission": {
                ActionEnum.DNS_DOMAIN_CREATE.id: can_create,
                ActionEnum.DNS_AUDIT_VIEW.id: can_view_global_audit,
            },
        }

    def retrieve_domain(self, domain: str) -> Dict:
        """返回域名详情，IP 从 DNS 读取。"""
        item = self._get_domain_item(domain)
        client = self._client(item["bk_biz_id"], item["bk_cloud_id"])
        item["ips"] = client.list_ips(item["domain"])
        item["readonly_reason"] = ""
        if item["maintain_type"] == MaintainType.CLUSTER.value:
            item["readonly_reason"] = _("该域名由集群托管，请在对应集群中操作")
        return item

    def create_domain(self, params: Dict) -> Dict:
        """新建自主维护域名，先写 DNS 再落库。"""
        domain = validate_domain(params["domain"])
        ips = validate_ips(params["ips"])
        owners = validate_owners(params.get("owners") or [self.username])
        remark = validate_remark(params.get("remark") or "")
        bk_cloud_id = params.get("bk_cloud_id", DEFAULT_BK_CLOUD_ID)
        self._reject_if_exists(domain, bk_cloud_id)
        client = self._client(PLAT_BIZ_ID, bk_cloud_id)
        client.create_ips(domain, ips)
        try:
            self._save_and_log(
                domain,
                [(AuditAction.CREATE.value, self._self_lines(ips, owners, remark))],
                lambda: DnsDomain.objects.create(
                    domain=domain,
                    maintain_type=MaintainType.SELF.value,
                    remark=remark,
                    owners=owners,
                    bk_biz_id=PLAT_BIZ_ID,
                    bk_cloud_id=bk_cloud_id,
                    creator=self.username,
                    updater=self.username,
                ),
            )
        except Exception:
            logger.exception("create dns domain meta failed, rollback dns, domain=%s", domain)
            try:
                client.delete_domain(domain)
            except Exception:  # pylint: disable=broad-except
                logger.exception("rollback dns domain failed, domain=%s", domain)
            raise
        return self.retrieve_domain(domain)

    def update_domain(self, params: Dict) -> Dict:
        """更新自主维护域名的 IP、负责人和备注。"""
        domain = normalize_domain(params["domain"])
        record = self._get_self_record(domain)
        ips = validate_ips(params["ips"])
        owners = validate_owners(params["owners"])
        remark = validate_remark(params.get("remark") or "")
        client = self._client(record.bk_biz_id, record.bk_cloud_id)
        added, removed = client.replace_ips(domain, ips)
        update_fields = ["updater", "update_at"]
        logs = []
        if added or removed:
            lines = []
            if added:
                lines.append(_("新增 IP: {}").format(self._join(added)))
            if removed:
                lines.append(_("删除 IP: {}").format(self._join(removed)))
            logs.append((AuditAction.UPDATE_IP.value, lines))
        if remark != record.remark:
            logs.append(
                (
                    AuditAction.UPDATE_REMARK.value,
                    [_("备注: {} → {}").format(record.remark or "-", remark or "-")],
                )
            )
            record.remark = remark
            update_fields.append("remark")
        if owners != list(record.owners or []):
            logs.append(
                (
                    AuditAction.UPDATE_OWNER.value,
                    [_("负责人: {} → {}").format(self._join(record.owners), self._join(owners))],
                )
            )
            record.owners = owners
            update_fields.append("owners")
        record.updater = self.username
        self._save_and_log(domain, logs, lambda: record.save(update_fields=update_fields))
        return self.retrieve_domain(domain)

    def delete_domain(self, params: Dict) -> Dict:
        """确认域名后删除自主维护记录和 DNS 映射。"""
        domain = normalize_domain(params["domain"])
        confirm_domain = normalize_domain(params["confirm_domain"])
        if confirm_domain != domain:
            raise ValidationError(_("请输入完整域名确认删除"))
        record = self._get_self_record(domain)
        client = self._client(record.bk_biz_id, record.bk_cloud_id)
        ips = client.list_ips(domain)
        client.delete_domain(domain)
        self._save_and_log(domain, [(AuditAction.DELETE.value, self._self_lines(ips))], record.delete)
        return {"domain": domain}

    def list_audits(self, params: Dict) -> Dict:
        """分页查询本域或全局操作日志。"""
        queryset = self._audit_queryset(params).order_by("-create_at", "-id")
        total = queryset.count()
        offset = params.get("offset") or 0
        limit = params.get("limit")
        page = queryset if limit in (None, -1) else queryset[offset : offset + limit]
        return {"count": total, "results": [self._audit_dict(item) for item in page]}

    def export_audits(self, params: Dict):
        """按当前筛选条件导出操作日志。"""
        from backend.utils.excel import ExcelHandler

        scope = params["scope"]
        rows = [self._audit_dict(item) for item in self._audit_queryset(params).order_by("-create_at", "-id")]
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

    def _collect_domains(self) -> List[Dict]:
        """汇总集群托管和自主维护域名，重名时保留集群托管。"""
        self_records = list(DnsDomain.objects.all())
        clusters = {cluster.id: cluster for cluster in Cluster.objects.exclude(immute_domain="")}
        entries = list(
            ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value).select_related("cluster")
        )
        for entry in entries:
            clusters[entry.cluster_id] = entry.cluster
        owners = self._cluster_owners(list(clusters.values()))
        cluster_items = {}
        for cluster in clusters.values():
            domain = normalize_domain(cluster.immute_domain)
            if domain:
                cluster_items[domain] = self._cluster_item(domain, cluster, owners.get(cluster.id, []))
        for entry in entries:
            domain = normalize_domain(entry.entry)
            if domain and domain not in cluster_items:
                cluster_items[domain] = self._cluster_item(domain, entry.cluster, owners.get(entry.cluster_id, []))
        items = dict(cluster_items)
        for record in self_records:
            if record.domain in items:
                continue
            items[record.domain] = self._self_item(record)
        return list(items.values())

    def _filter_domains(self, items: List[Dict], params: Dict) -> List[Dict]:
        """按域名、维护方式、负责人过滤。"""
        domain = normalize_domain(params.get("domain") or "")
        maintain_type = params.get("maintain_type") or ""
        owner = (params.get("owner") or "").strip()
        mine = bool(params.get("mine"))
        filtered = []
        for item in items:
            if domain and domain not in item["domain"]:
                continue
            if maintain_type and item["maintain_type"] != maintain_type:
                continue
            if owner and owner not in item["owners"]:
                continue
            if mine and self.username not in item["owners"]:
                continue
            filtered.append(item)
        return filtered

    def _get_domain_item(self, domain: str) -> Dict:
        """按域名取出一条列表记录。"""
        normalized = normalize_domain(domain)
        for item in self._collect_domains():
            if item["domain"] == normalized:
                return item
        raise ValidationError(_("域名不存在"))

    def _get_self_record(self, domain: str) -> DnsDomain:
        """取自主维护记录，集群托管域名直接拒绝。"""
        cluster = self._find_cluster(domain)
        if cluster is not None:
            raise ValidationError(_("该域名由集群托管，请在对应集群中操作"))
        try:
            return DnsDomain.objects.get(domain=domain)
        except DnsDomain.DoesNotExist:
            raise ValidationError(_("域名不存在"))

    def _reject_if_exists(self, domain: str, bk_cloud_id: int):
        """域名已在库、集群或 DNS 中存在时拒绝创建。"""
        if DnsDomain.objects.filter(domain=domain).exists() or self._find_cluster(domain) is not None:
            raise ValidationError(_("域名已存在"))
        if self._client(PLAT_BIZ_ID, bk_cloud_id).has_mapping(domain):
            raise ValidationError(_("域名已存在"))

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

    def _cluster_owners(self, clusters: List[Cluster]) -> Dict[int, List[str]]:
        """取每个集群对应组件的主 DBA。"""
        biz_ids = {cluster.bk_biz_id for cluster in clusters}
        admins = DBAdministrator.list_biz_admins_bulk(biz_ids) if biz_ids else {}
        owners = {}
        for cluster in clusters:
            try:
                db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
            except ValueError:
                owners[cluster.id] = []
                continue
            users = []
            for item in admins.get(cluster.bk_biz_id, []):
                if item["db_type"] == db_type:
                    users = item["users"] or []
                    break
            owners[cluster.id] = users[:1]
        return owners

    def _cluster_item(self, domain: str, cluster: Cluster, owners: List[str]) -> Dict:
        """组装一条集群托管域名。"""
        return {
            "domain": domain,
            "maintain_type": MaintainType.CLUSTER.value,
            "maintain_type_display": str(MaintainType.get_choice_label(MaintainType.CLUSTER.value)),
            "owners": owners,
            "remark": "",
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_id": cluster.id,
        }

    def _self_item(self, record: DnsDomain) -> Dict:
        """组装一条自主维护域名。"""
        return {
            "domain": record.domain,
            "maintain_type": record.maintain_type,
            "maintain_type_display": str(MaintainType.get_choice_label(record.maintain_type)),
            "owners": list(record.owners or []),
            "remark": record.remark,
            "bk_biz_id": record.bk_biz_id,
            "bk_cloud_id": record.bk_cloud_id,
            "cluster_id": None,
        }

    def _audit_queryset(self, params: Dict):
        """按范围、域名、操作人和动作过滤日志。"""
        queryset = DnsDomainAuditLog.objects.all()
        scope = params["scope"]
        if scope == AUDIT_SCOPE_DOMAIN:
            queryset = queryset.filter(domain=normalize_domain(params["domain"]))
        keyword = (params.get("keyword") or "").strip()
        if keyword:
            if scope == AUDIT_SCOPE_GLOBAL:
                queryset = queryset.filter(domain__icontains=keyword)
            else:
                queryset = queryset.filter(operator__icontains=keyword)
        operator = (params.get("operator") or "").strip()
        if operator:
            queryset = queryset.filter(operator__icontains=operator)
        action = params.get("action") or ""
        if action:
            queryset = queryset.filter(action=action)
        domain = normalize_domain(params.get("domain") or "")
        if scope == AUDIT_SCOPE_GLOBAL and domain and domain != keyword:
            queryset = queryset.filter(domain__icontains=domain)
        return queryset

    def _audit_dict(self, item: DnsDomainAuditLog) -> Dict:
        """把一条日志转成接口字段。"""
        return {
            "id": item.id,
            "domain": item.domain,
            "operator": item.operator,
            "client_ip": item.client_ip,
            "action": item.action,
            "action_display": str(AuditAction.get_choice_label(item.action)),
            "change_lines": list(item.change_lines or []),
            "create_at": timezone.localtime(item.create_at).strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _save_and_log(self, domain: str, logs: List, mutate):
        """在同一事务里落库，并写入操作日志。"""
        with transaction.atomic():
            mutate()
            for action, lines in logs:
                self._write_log(domain, action, lines)

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

    def _manageable_domains(self, domains: List[str]) -> set:
        """批量判断当前用户能否管理这些域名。"""
        if not domains:
            return set()
        resources = [[ResourceEnum.DNS_DOMAIN.create_instance(domain)] for domain in domains]
        result = self._permission().batch_is_allowed([ActionEnum.DNS_MANAGE], resources) or {}
        action_id = ActionEnum.DNS_MANAGE.id
        return {domain for domain in domains if (result.get(str(domain)) or {}).get(action_id)}

    def _permission(self) -> Permission:
        """构造当前用户的权限客户端。"""
        if self.request is not None:
            return Permission(request=self.request)
        return Permission(username=self.username)

    @staticmethod
    def _client(bk_biz_id: int, bk_cloud_id: int) -> DnsDomainClient:
        """按业务和云区域构造 DNS 客户端。"""
        return DnsDomainClient(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id)

    @staticmethod
    def _join(values) -> str:
        """把列表拼成日志里的展示文本。"""
        values = [str(value) for value in values or [] if str(value)]
        return ", ".join(values) if values else "-"
