# -*- coding: utf-8 -*-
"""
TenDBCluster 接入层全毁灾难恢复单据校验。
按 IP 列表非空分支严格校验：
  - master_new 非空 → master_old 必填且严格匹配元数据 SPIDER_MASTER
  - slave_new 非空  → slave_old 必填且严格匹配元数据 SPIDER_SLAVE
  - 仅恢复 slave 时：L1（DBMeta RUNNING）+ L3（DRS 在中控 admin_port 探活）双层校验
  - 同时恢复时：master/slave 新 IP 不可重叠
"""
from typing import List

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterEntryRole, ClusterType, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ClusterEntry, ProxyInstance
from backend.db_report.mysql_backup.handers import MySQLBackupHandler
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator
from backend.flow.utils.spider.spider_disaster_recover import probe_running_ctl_via_drs, resolve_spider_ctl_ports


class PrivilegeRecoveryMode:
    FROM_SPIDER_GRANT_BACKUP = "from_spider_grant_backup"
    ACCOUNT_RULES_ONLY = "account_rules_only"


class TenDBClusterSpiderLayerDisasterRecoverFlowValidator(MysqlBaseValidator):
    def run_check_for_info(self, info: dict, index: int) -> list:
        row_key = info.get("row_key", "")
        error_msg_list: List[str] = []

        cluster = Cluster.objects.filter(id=int(info["cluster_id"])).first()
        if not cluster:
            error_msg_list.append(_("集群 {} 不存在\n").format(info["cluster_id"]))
            return error_msg_list

        # ── 通用集群校验 ────────────────────────────────────────────────
        if cluster.cluster_type != ClusterType.TenDBCluster.value:
            error_msg_list.append(_("集群 {} 类型非 TenDBCluster，无法执行接入层灾难恢复\n").format(cluster.id))
            return error_msg_list

        can_access, access_msg = cluster.can_access()
        if not can_access:
            error_msg_list.append(_("集群 {}（{}）当前不可操作: {}\n").format(cluster.id, cluster.immute_domain, access_msg))
            return error_msg_list

        # 端口解析（异常即追加错误）
        try:
            resolve_spider_ctl_ports(cluster, info.get("spider_port"), info.get("ctl_port"))
        except ValueError as exc:
            error_msg_list.append("{}\n".format(str(exc)))

        # ── 角色识别：基于 IP 列表非空 ──────────────────────────────────
        master_new = info.get("spider_master_new_ip_list") or []
        master_old = info.get("spider_master_old_ip_list") or []
        slave_new = info.get("spider_slave_new_ip_list") or []
        slave_old = info.get("spider_slave_old_ip_list") or []

        if not master_new and not slave_new:
            error_msg_list.append(_("spider_master_new_ip_list 与 spider_slave_new_ip_list 不能同时为空\n"))
            return error_msg_list

        # ── master 段约束 ──────────────────────────────────────────────
        error_msg_list.extend(
            self._check_role_segment(
                cluster=cluster,
                role_label="spider_master",
                meta_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
                new_list=master_new,
                old_list=master_old,
                index=index,
                row_key=row_key,
            )
        )

        # ── slave 段约束 ───────────────────────────────────────────────
        error_msg_list.extend(
            self._check_role_segment(
                cluster=cluster,
                role_label="spider_slave",
                meta_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value,
                new_list=slave_new,
                old_list=slave_old,
                index=index,
                row_key=row_key,
            )
        )

        # ── 仅恢复 slave 时强制 L1+L3 中控校验 + SLAVE_ENTRY 存在 ───────
        if slave_new and not master_new:
            error_msg_list.extend(self._check_ctl_alive_for_slave_only(cluster))
        if slave_new:
            error_msg_list.extend(self._check_slave_entry_exists(cluster))

        # ── 同时恢复时：master/slave 新 IP 不允许重叠 ───────────────────
        if master_new and slave_new:
            overlap = {h["ip"] for h in master_new} & {h["ip"] for h in slave_new}
            if overlap:
                error_msg_list.append(
                    _("spider_master_new_ip_list 与 spider_slave_new_ip_list 存在重叠 IP: {}\n").format(sorted(overlap))
                )

        # ── 备份模式校验：缺省视为 from_spider_grant_backup，兼容直调 FlowTestView ──
        mode = info.get("privilege_recovery_mode") or PrivilegeRecoveryMode.FROM_SPIDER_GRANT_BACKUP
        if mode not in (PrivilegeRecoveryMode.FROM_SPIDER_GRANT_BACKUP, PrivilegeRecoveryMode.ACCOUNT_RULES_ONLY):
            error_msg_list.append(_("privilege_recovery_mode 非法\n"))
        elif mode == PrivilegeRecoveryMode.FROM_SPIDER_GRANT_BACKUP:
            handler = MySQLBackupHandler(cluster_id=cluster.id, deadlines_days=7)
            backup = handler.get_tendbcluster_spider_layer_grant_priv_backup_info(
                spider_priv_backup_id=info.get("spider_priv_backup_id") or None,
            )
            if not backup:
                error_msg_list.append(_("未找到 Spider/tdbctl grant 备份，请检查备份或改用 account_rules_only\n"))

        return error_msg_list

    # ─────────────────────────────────────────────────────────────────────
    # 各分支校验子函数
    # ─────────────────────────────────────────────────────────────────────
    def _check_role_segment(
        self,
        *,
        cluster: Cluster,
        role_label: str,
        meta_role: str,
        new_list: list,
        old_list: list,
        index: int,
        row_key: str,
    ) -> List[str]:
        """通用：按角色检查 new / old IP 列表是否合法。"""
        errs: List[str] = []
        if not new_list:
            if old_list:
                errs.append(_("{}_new_ip_list 为空时不允许提供 {}_old_ip_list\n").format(role_label, role_label))
            return errs

        # IP 可用性
        log_format_tag = self.create_log_tag(field="{}_new_ip_list".format(role_label), index=index, row_key=row_key)
        ip_err = self.pre_check_ip([h["ip"] for h in new_list], **log_format_tag)
        if ip_err:
            errs.append(ip_err)

        # old_list 严格匹配元数据
        if not old_list:
            errs.append(_("{}_new_ip_list 非空时 {}_old_ip_list 必填\n").format(role_label, role_label))
            return errs

        meta_ips = set(
            ProxyInstance.objects.filter(
                cluster=cluster,
                tendbclusterspiderext__spider_role=meta_role,
            ).values_list("machine__ip", flat=True)
        )
        for h in old_list:
            ip = h.get("ip")
            if ip and ip not in meta_ips:
                errs.append(_("{}_old_ip_list 中 IP {} 不在元数据 {} 中\n").format(role_label, ip, meta_role))
        return errs

    def _check_ctl_alive_for_slave_only(self, cluster: Cluster) -> List[str]:
        """
        L1 + L3 双层校验：
          L1: DBMeta status=RUNNING 的 spider_master ≥ 1 个
          L3: 至少 1 个 RUNNING 中控通过 DRS `select @@version` 探活
        """
        running_ctls = list(
            ProxyInstance.objects.filter(
                cluster=cluster,
                tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value,
                status=InstanceStatus.RUNNING,
            )
        )
        if not running_ctls:
            return [_("仅恢复 spider_slave 时 DBMeta 中无 RUNNING 中控（spider_master）\n")]

        alive_ip = probe_running_ctl_via_drs(cluster, running_ctls)
        if not alive_ip:
            return [_("仅恢复 spider_slave 时所有中控（spider_master.admin_port）DRS 探活均失败，" "请确认中控进程与端口正常\n")]
        return []

    def _check_slave_entry_exists(self, cluster: Cluster) -> List[str]:
        exists = ClusterEntry.objects.filter(
            cluster=cluster,
            role=ClusterEntryRole.SLAVE_ENTRY.value,
        ).exists()
        if not exists:
            return [_("集群 {} 不存在 SLAVE_ENTRY 从域名\n").format(cluster.id)]
        return []

    def __call__(self):
        error_msgs = []
        dup_err = self.pre_check_duplicate_cluster_ids("cluster_id")
        if dup_err:
            error_msgs.append(dup_err)
        for index, info in enumerate(self.data.get("infos") or []):
            error_msgs += self.run_check_for_info(info, index)
        if error_msgs:
            return error_msgs
        return None
