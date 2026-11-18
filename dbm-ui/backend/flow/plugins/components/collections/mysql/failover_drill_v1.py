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
import importlib
import json
from datetime import datetime, timedelta, timezone
from typing import List

from django.db.models import F, Value
from django.db.models.functions import Concat
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.components.dns.client import DnsApi
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_periodic_task.constants import FailoverDrillVersion, failover_drill_queue_version
from backend.db_report.enums import ReportStateType
from backend.db_report.models.failover_drill_report import FailoverDrillReport
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.failover_drill_dbha import query_switch_queue


class DrillClusterDnsDeleteService(BaseService):
    """按演练域名删除 DNS。域名不存在算成功；记录还在但删不掉则失败，流程停在这里。"""

    def _domain_names(self, kwargs, bk_biz_id, bk_cloud_id):
        names = []
        for key in ("immute_domain", "slave_domain"):
            name = "{}".format(kwargs.get(key) or "").strip()
            if name and name not in names:
                names.append(name)
        domain = names[0] if names else ""
        cluster = None
        if domain:
            cluster = Cluster.objects.filter(
                bk_biz_id=bk_biz_id, immute_domain=domain, bk_cloud_id=bk_cloud_id
            ).first()
        if cluster is None:
            return names
        entries = ClusterEntry.objects.filter(
            cluster=cluster,
            cluster_entry_type__in=[ClusterEntryType.DNS, ClusterEntryType.CLBDNS],
        )
        for entry in entries:
            if entry.entry and entry.entry not in names:
                names.append(entry.entry)
        return names

    @staticmethod
    def _absent(err) -> bool:
        text = "{}".format(err).lower()
        return "not exist" in text or "not found" in text or "no such" in text or "不存在" in text or "404" in text

    def _delete_one(self, dns, bk_biz_id, bk_cloud_id, domain) -> bool:
        try:
            detail = dns.get_domain(domain)
        except Exception as err:
            if self._absent(err):
                self.log_info(_("演练域名 {} 不存在，无需删除").format(domain))
                return True
            self.log_exception(_("查询演练域名 {} 失败: {}").format(domain, err))
            return False
        if not detail:
            self.log_info(_("演练域名 {} 不存在，无需删除").format(domain))
            return True
        try:
            DnsApi.delete_domain(
                {
                    "app": str(bk_biz_id),
                    "domains": [{"domain_name": dns.format_domain(domain)}],
                    "bk_cloud_id": bk_cloud_id,
                }
            )
        except Exception as err:
            if self._absent(err):
                self.log_info(_("演练域名 {} 不存在，无需删除").format(domain))
                return True
            self.log_exception(_("删除演练域名 {} 失败: {}").format(domain, err))
            return False
        try:
            left = dns.get_domain(domain)
        except Exception as err:
            if self._absent(err):
                self.log_info(_("已删除演练域名 {}").format(domain))
                return True
            self.log_exception(_("删除后复查演练域名 {} 失败: {}").format(domain, err))
            return False
        if left:
            self.log_error(_("演练域名 {} 删除后仍然存在").format(domain))
            return False
        self.log_info(_("已删除演练域名 {}").format(domain))
        return True

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        bk_biz_id = int(kwargs["bk_biz_id"])
        bk_cloud_id = int(kwargs["bk_cloud_id"])
        names = self._domain_names(kwargs, bk_biz_id, bk_cloud_id)
        if not names:
            self.log_error(_("没有演练域名可删除"))
            return False
        dns = DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id)
        for domain in names:
            if not self._delete_one(dns, bk_biz_id, bk_cloud_id, domain):
                return False
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class DrillClusterDnsDeleteComponent(Component):
    name = __name__
    code = "mysql_failover_drill_v1_delete_dns"
    bound_service = DrillClusterDnsDeleteService


class DrillClusterDecommissionService(BaseService):
    """按主域名下架元数据。集群不存在则跳过。TenDBHA 和 TenDBCluster 各走自己的 handler。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        domain = kwargs["immute_domain"]
        bk_biz_id = int(kwargs["bk_biz_id"])
        bk_cloud_id = int(kwargs["bk_cloud_id"])
        cluster = Cluster.objects.filter(bk_biz_id=bk_biz_id, immute_domain=domain, bk_cloud_id=bk_cloud_id).first()
        if cluster is None:
            self.log_info(_("集群 {} 不在元数据里，跳过下架元数据").format(domain))
            return True
        try:
            from backend.db_meta.enums import ClusterType

            if cluster.cluster_type == ClusterType.TenDBCluster.value:
                from backend.db_meta.api.cluster.tendbcluster.handler import TenDBClusterClusterHandler as Handler
            elif cluster.cluster_type == ClusterType.TenDBHA.value:
                from backend.db_meta.api.cluster.tendbha.handler import TenDBHAClusterHandler as Handler
            else:
                self.log_error(_("演练下架不支持集群类型 {}").format(cluster.cluster_type))
                return False
            Handler(bk_biz_id=bk_biz_id, cluster_id=cluster.id).decommission()
        except Exception as err:
            self.log_exception(_("演练集群下架元数据失败: {}").format(err))
            return False
        self.log_info(_("已下架演练集群 {} 的元数据").format(domain))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class DrillClusterDecommissionComponent(Component):
    name = __name__
    code = "mysql_failover_drill_v1_decommission"
    bound_service = DrillClusterDecommissionService


class DrillDbhaReportService(BaseService):
    """把 DBHA 切换结果写进演练报告。切换失败只记 abnormal，不中断回池。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        main_task_id = kwargs["main_task_id"]
        raw_targets = kwargs.get("drill_ips") or {}
        if isinstance(raw_targets, dict):
            targets = list(raw_targets.items())
            drill_ips = list(raw_targets.values())
        else:
            targets = []
            drill_ips = list(raw_targets)
        finished_time = datetime.now().astimezone(timezone.utc)
        start_time = finished_time - timedelta(hours=8)
        dbha_infos = {"error": ""}
        try:
            code, msg, resp_data = query_switch_queue(
                dbha_version=failover_drill_queue_version(kwargs.get("dbha_version") or FailoverDrillVersion.V1.value),
                app=str(kwargs["bk_biz_id"]),
                start_time=start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                finished_time=finished_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                extra_v1_args={"cloud_id": kwargs["bk_cloud_id"]},
            )
            if code == 0:
                ip_to_type = {ip: instance_type for instance_type, ip in targets}
                for item in resp_data:
                    for ip in drill_ips:
                        if item.get("ip") == ip or item.get("slave_ip") == ip:
                            db_type = item.get("db_type")
                            if db_type:
                                dbha_infos[db_type] = item
                            instance_type = ip_to_type.get(ip)
                            if instance_type:
                                dbha_infos[instance_type] = item
            else:
                dbha_infos["error"] = "HADB service query failed. code:{} msg:{}".format(code, msg)
        except Exception as err:
            dbha_infos["error"] = "HADB service query error:{}".format(err)
            self.log_exception(_("查询 DBHA 切换记录失败: {}").format(err))

        record = importlib.import_module("backend.db_periodic_task.local_tasks.mysql_failover_drill_v1.record")
        type_results = []
        for instance_type, ip in targets:
            info = dbha_infos.get(instance_type)
            if dbha_infos["error"]:
                dbha_result = record.DBHA_QUERY_ERROR
                detail = dbha_infos["error"]
                dbha_status = ""
                switch_start_time = None
                switch_finished_time = None
            elif isinstance(info, dict):
                dbha_result = record.DBHA_SWITCHED
                detail = ""
                dbha_status = info.get("status") or ""
                switch_start_time = info.get("switch_start_time") or None
                switch_finished_time = info.get("switch_finished_time") or None
            else:
                dbha_result = record.DBHA_TIMEOUT
                detail = _("未查到该实例类型的切换记录")
                dbha_status = ""
                switch_start_time = None
                switch_finished_time = None
            type_results.append(
                {
                    "instance_type": instance_type,
                    "ip": ip,
                    "dbha_result": dbha_result,
                    "dbha_status": dbha_status,
                    "error_message": detail,
                    "switch_start_time": switch_start_time,
                    "switch_finished_time": switch_finished_time,
                }
            )
        if type_results:
            record.mark_dbha_results(main_task_id, type_results)
            switch_ok = all(item["dbha_result"] == record.DBHA_SWITCHED for item in type_results)
        else:
            matched = len([key for key in dbha_infos if key != "error"])
            if matched >= 2 and not dbha_infos["error"]:
                dbha_result = record.DBHA_SWITCHED
                detail = ""
            elif dbha_infos["error"]:
                dbha_result = record.DBHA_QUERY_ERROR
                detail = dbha_infos["error"]
            else:
                dbha_result = record.DBHA_TIMEOUT
                detail = _("未查到足够的切换记录，matched={}").format(matched)
            record.mark_dbha_result(main_task_id, dbha_result, detail)
            switch_ok = dbha_result == record.DBHA_SWITCHED
        reports = FailoverDrillReport.objects.filter(main_task_id=main_task_id)
        for report in reports:
            info = dbha_infos.get(report.instance_type)
            if isinstance(info, dict):
                report.dbha_info = json.dumps(info, ensure_ascii=False, default=str)
                report.dbha_status = info.get("status", "failed")
                report.state = (
                    ReportStateType.ABNORMAL.value if report.dbha_status == "failed" else ReportStateType.NORMAL.value
                )
                report.switch_start_time = info.get("switch_start_time") or None
                report.switch_finished_time = info.get("switch_finished_time") or None
            else:
                report.dbha_info = dbha_infos["error"]
                report.state = ReportStateType.ABNORMAL.value
            report.status = switch_ok
            report.save()

        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        summary = _("[{}] DBHA 切换{}，继续下架并退回资源").format(timestamp, _("成功") if switch_ok else _("未完成"))
        FailoverDrillReport.objects.filter(main_task_id=main_task_id).update(
            task_info=Concat(F("task_info"), Value("\n"), Value(summary))
        )
        self.log_info(summary)
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class DrillDbhaReportComponent(Component):
    name = __name__
    code = "mysql_failover_drill_v1_dbha_report"
    bound_service = DrillDbhaReportService
