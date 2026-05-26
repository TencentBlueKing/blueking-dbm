# -*- coding: utf-8 -*-
"""
TenDBCluster 接入层全毁灾难恢复单据校验。

⚠️ 校验阶段尚未分配/补齐 *_new_ip_list（新机器信息后续才会确定），
   因此本 Validator 不做任何依赖 new 列表的校验，仅做与 new 无关的元数据/参数校验：
     - 集群存在性 / 类型 / 是否可操作
     - spider_port / ctl_port 端口解析
     - privilege_recovery_mode 合法性及对应备份存在性
   涉及 new/old IP 列表、中控探活、SLAVE_ENTRY 存在等校验，
   需在资源分配后由 flow 自身或专门的 pre-flight 阶段执行。
"""
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.mysql_backup.handers import MySQLBackupHandler
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator
from backend.flow.utils.spider.spider_disaster_recover import resolve_spider_ctl_ports


class PrivilegeRecoveryMode:
    FROM_SPIDER_GRANT_BACKUP = "from_spider_grant_backup"
    ACCOUNT_RULES_ONLY = "account_rules_only"


class TenDBClusterSpiderLayerDisasterRecoverFlowValidator(MysqlBaseValidator):
    def run_check_for_info(self, info: dict, index: int) -> list:
        error_msg_list: list = []

        cluster = Cluster.objects.filter(id=int(info["cluster_id"])).first()
        if not cluster:
            error_msg_list.append(_("集群 {} 不存在\n").format(info["cluster_id"]))
            return error_msg_list

        if cluster.cluster_type != ClusterType.TenDBCluster.value:
            error_msg_list.append(_("集群 {} 类型非 TenDBCluster，无法执行接入层灾难恢复\n").format(cluster.id))
            return error_msg_list

        can_access, access_msg = cluster.can_access()
        if not can_access:
            error_msg_list.append(_("集群 {}（{}）当前不可操作: {}\n").format(cluster.id, cluster.immute_domain, access_msg))
            return error_msg_list

        try:
            resolve_spider_ctl_ports(cluster, info.get("spider_port"), info.get("ctl_port"))
        except ValueError as exc:
            error_msg_list.append("{}\n".format(str(exc)))

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
