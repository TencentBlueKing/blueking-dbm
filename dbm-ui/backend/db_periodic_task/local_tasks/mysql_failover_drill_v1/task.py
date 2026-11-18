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

from celery.schedules import crontab
from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import LogicalCity
from backend.db_periodic_task.constants import FailoverDrillVersion
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.mysql_failover_drill_v1.record import (
    attach_root,
    dbha_v2_switch_open,
    dbha_version_of,
    drill_cluster_name,
    fail_flow_start,
    fail_resource_apply,
    finish_resource_apply,
    mark_emergency_return,
    open_city_run,
    open_dbha_rows,
    record_skip,
    select_configs_to_start,
    sync_run_by_main_task,
    sync_running_runs,
)
from backend.db_periodic_task.models import MysqlFailoverDrillV1Config
from backend.db_report.enums import ReportStateType
from backend.db_report.models.failover_drill_report import FailoverDrillReport
from backend.db_services.cmdb.biz import get_resource_biz
from backend.db_services.dbresource.exceptions import ResourceApplyException, ResourceApplyInsufficientException
from backend.flow.engine.bamboo.scene.mysql.mysql_failover_drill_v1_flow import (
    MysqlFailoverDrillV1Flow,
    build_dbha_trigger_scripts,
)
from backend.flow.engine.bamboo.scene.spider.tendbcluster_failover_drill_v1_flow import (
    DRILL_SHARD_NUM,
    TendbClusterFailoverDrillV1Flow,
)
from backend.flow.models import FlowTree
from backend.ticket.constants import ResourceApplyErrCode, TicketType
from backend.utils.basic import generate_root_id

logger = logging.getLogger("celery")


def _init_report(
    main_task_id: str,
    bk_biz_id: int,
    bk_cloud_id: int,
    domain: str,
    city: str,
    cluster_type: str,
    instance_types,
    version: str,
):
    base = {
        "state": ReportStateType.WARNING.value,
        "bk_biz_id": bk_biz_id,
        "bk_cloud_id": bk_cloud_id,
        "status": False,
        "main_task_id": main_task_id,
        "cluster_domain": domain,
        "cluster_type": cluster_type,
        "city": city,
        "instance_type": instance_types[0],
        "version": dbha_version_of(version),
    }
    FailoverDrillReport.objects.create(**base)
    base["instance_type"] = instance_types[1]
    FailoverDrillReport.objects.create(**base)


def _apply_hosts(bk_biz_id: int, bk_cloud_id: int, city: str, labels: list, task_id: str, bill_type: str) -> list:
    apply_params = {
        "for_biz_id": bk_biz_id,
        "resource_type": "mysql",
        "details": [
            {
                "bk_cloud_id": bk_cloud_id,
                "group_mark": "backend_group",
                "location_spec": {"city": city},
                "count": 4,
                "labels": labels,
            }
        ],
        "task_id": task_id,
        "bill_id": task_id,
        "bill_type": bill_type,
        "operator": "dba",
    }
    resp = DBResourceApi.resource_apply(params=apply_params, raw=True)
    if resp["code"] == ResourceApplyErrCode.RESOURCE_LAKE:
        raise ResourceApplyInsufficientException(_("资源不足申请失败，请前往补货后重试{}").format(resp.get("message")))
    if resp["code"] != 0:
        raise ResourceApplyException(
            _("资源池相关服务出现未知异常，请联系管理员处理。错误信息: [{}]{}").format(resp["code"], resp.get("message"))
        )
    hosts = []
    for item in resp["data"][0]["data"]:
        hosts.append(
            {
                "ip": item["ip"],
                "bk_host_id": item["bk_host_id"],
                "bk_cloud_id": bk_cloud_id,
                "bk_biz_id": bk_biz_id,
            }
        )
    if len(hosts) < 4:
        raise ResourceApplyException(_("资源申请返回机器数量不足 4 台"))
    return hosts


def _return_hosts(bk_biz_id: int, labels: list, hosts: list, task_id: str):
    """流程还没拉起来时，把已经申请到的机器带标签退回去。"""
    params = {
        "for_biz": bk_biz_id,
        "bk_biz_id": get_resource_biz(),
        "resource_type": "mysql",
        "hosts": [
            {"ip": host["ip"], "host_id": host["bk_host_id"], "bk_cloud_id": host["bk_cloud_id"]} for host in hosts
        ],
        "labels": labels,
        "task_id": task_id,
        "bill_id": task_id,
        "bill_type": "RESOURCE_IMPORT",
        "operator": "dba",
    }
    resp = DBResourceApi.resource_import(params=params, raw=True)
    if resp["code"] != 0:
        logger.error("return drill hosts failed: %s", resp)
        return False
    return True


def _machine(host: dict) -> dict:
    return {
        "ip": host["ip"],
        "bk_host_id": host["bk_host_id"],
        "bk_biz_id": host["bk_biz_id"],
        "bk_cloud_id": host["bk_cloud_id"],
    }


def _build_city_plan(conf: MysqlFailoverDrillV1Config, city: str) -> dict:
    cluster_type = conf.cluster_type
    is_cluster = cluster_type == ClusterType.TenDBCluster.value
    main_task_id = generate_root_id()
    version = dbha_version_of(conf.version)
    run = open_city_run(
        conf.bk_biz_id,
        conf.bk_cloud_id,
        city,
        cluster_type,
        main_task_id,
        conf.labels,
        version,
    )
    hosts = None
    emergency = False
    try:
        logical_city_id = LogicalCity.objects.get(name=city).id
        add_cmd, clean_cmd = build_dbha_trigger_scripts(
            bk_cloud_id=conf.bk_cloud_id,
            logical_city_id=logical_city_id,
            cluster_type=cluster_type,
            version=version,
        )
        bill_type = "TENDBCLUSTER_APPLY" if is_cluster else "MYSQL_HA_APPLY"
        hosts = _apply_hosts(conf.bk_biz_id, conf.bk_cloud_id, city, conf.labels, main_task_id, bill_type)
        cluster_name = drill_cluster_name(conf.city_abbr, version)
        if is_cluster:
            master_domain = "spider.{}.dbatest.db".format(cluster_name)
            slave_domain = ""
            instance_types = ("spider", "remote")
        else:
            master_domain = "failover.{}.dbatest.db".format(cluster_name)
            slave_domain = "failover.{}.dbatest.dr".format(cluster_name)
            instance_types = ("proxy", "backend")
        try:
            _init_report(
                main_task_id,
                conf.bk_biz_id,
                conf.bk_cloud_id,
                master_domain,
                city,
                cluster_type,
                instance_types,
                version,
            )
        except Exception as err:
            returned = _return_hosts(conf.bk_biz_id, conf.labels, hosts, main_task_id)
            mark_emergency_return(main_task_id, returned, "{}".format(err))
            emergency = True
            raise
        host_rows = [
            {"ip": host["ip"], "host_id": host["bk_host_id"], "bk_cloud_id": host["bk_cloud_id"]} for host in hosts
        ]
        finish_resource_apply(run, host_rows, master_domain, slave_domain)
    except Exception as err:
        if not emergency:
            fail_resource_apply(run, "{}".format(err))
        raise
    storage_hosts = hosts[:2]
    access_hosts = hosts[2:]
    if is_cluster:
        drill_ips = {"remote": storage_hosts[0]["ip"], "spider": access_hosts[0]["ip"]}
    else:
        drill_ips = {"backend": storage_hosts[0]["ip"], "proxy": access_hosts[0]["ip"]}
    open_dbha_rows(run, drill_ips)
    plan = {
        "city": city,
        "bk_biz_id": conf.bk_biz_id,
        "bk_cloud_id": conf.bk_cloud_id,
        "db_module_id": conf.db_module_id,
        "module": str(conf.db_module_id),
        "charset": conf.charset,
        "db_version": conf.db_version,
        "disaster_tolerance_level": conf.disaster_tolerance_level,
        "start_mysql_port": conf.start_mysql_port,
        "start_proxy_port": conf.start_proxy_port,
        "main_task_id": main_task_id,
        "dbha_version": version,
        "labels": conf.labels,
        "add_iptables": add_cmd,
        "clean_iptables": clean_cmd,
        "drill_ips": drill_ips,
        "hosts": host_rows,
        "apply_infos": [
            {
                "clusters": [{"name": cluster_name, "master": master_domain, "slave": slave_domain}],
                "mysql_ip_list": storage_hosts,
                "proxy_ip_list": access_hosts,
            }
        ],
    }
    if is_cluster:
        plan.update(
            {
                "cluster_name": cluster_name,
                "immutable_domain": master_domain,
                "spider_port": conf.start_proxy_port,
                "spider_version": conf.spider_version,
                "cluster_shard_num": DRILL_SHARD_NUM,
                "remote_shard_num": DRILL_SHARD_NUM,
                "mysql_ip_list": [_machine(host) for host in storage_hosts],
                "spider_ip_list": [_machine(host) for host in access_hosts],
                "remote_group": [
                    {"master": _machine(storage_hosts[0]), "slave": _machine(storage_hosts[1])},
                ],
                "resource_spec": {"remote": {"id": 0}, "spider": {"id": 0}},
            }
        )
    return plan


def _build_ticket_data(root_id: str, city: dict) -> dict:
    """一座城市一条 flow。单据就是这座城市的计划，再加上 flow 固定字段。"""
    data = dict(city)
    data.update(
        created_by="dba",
        ticket_type=TicketType.MYSQL_FAILOVER_DRILL.value,
        uid=root_id,
        zone_list=[],
        inst_num=1,
        apply_clb=False,
        force=True,
    )
    data.setdefault("resource_spec", {"backend": {"id": 0}, "proxy": {"id": 0}})
    return data


def _emergency_return_city(city: dict, error_message: str):
    """flow 没建起来时，把这座城市已经申请到的机器带标签退回，并记下没建起来的原因。"""
    allocated = [
        {
            "ip": host["ip"],
            "bk_host_id": host["host_id"],
            "bk_cloud_id": host["bk_cloud_id"],
        }
        for host in city["hosts"]
    ]
    returned = _return_hosts(city["bk_biz_id"], city["labels"], allocated, city["main_task_id"])
    mark_emergency_return(city["main_task_id"], returned, error_message)


def _run_failover_drill_v1(cluster_type: str, flow_cls, version: str):
    """一个集群类型、一个 DBHA 版本一次。v1 和 v2 不在同一个任务里申请机器。"""
    configs = MysqlFailoverDrillV1Config.select_enabled(
        MysqlFailoverDrillV1Config.objects.filter(cluster_type=cluster_type, version=version).order_by("id")
    )
    if not configs:
        logger.info("failover drill has no enabled city: type=%s version=%s", cluster_type, version)
        return
    configs, skipped = select_configs_to_start(configs)
    for conf, reason in skipped:
        record_skip(conf, reason)
        logger.info(
            "skip failover drill v1 city=%s type=%s version=%s reason=%s",
            conf.city,
            cluster_type,
            conf.version,
            reason,
        )

    for conf in configs:
        if not dbha_v2_switch_open(conf.version):
            record_skip(conf, "switch_off")
            logger.info(
                "skip failover drill v1 city=%s type=%s version=%s reason=switch_off",
                conf.city,
                cluster_type,
                conf.version,
            )
            continue
        try:
            city = _build_city_plan(conf, conf.city)
        except Exception as err:
            logger.exception("prepare failover drill city %s failed: %s", conf.city, err)
            continue
        root_id = generate_root_id()
        attach_root([city["main_task_id"]], root_id)
        ticket_data = _build_ticket_data(root_id, city)
        logger.info(
            "start failover drill flow %s type=%s city=%s",
            root_id,
            cluster_type,
            city["city"],
        )
        try:
            flow_cls(root_id=root_id, data=ticket_data).run()
        except Exception as err:
            logger.exception("failed to start failover drill flow %s city=%s", root_id, city["city"])
            message = "{}".format(err)
            if not FlowTree.objects.filter(root_id=root_id).exists():
                _emergency_return_city(city, message)
            else:
                fail_flow_start(city["main_task_id"], message)
            continue
        sync_run_by_main_task(city["main_task_id"])


@register_periodic_task(run_every=crontab(minute="*/5"))
def mysql_failover_drill_v1_sync_task():
    """按 root_id 读 flow_node，回写还在跑的演练结果。"""
    sync_running_runs()


@register_periodic_task(run_every=crontab(minute=0, hour=9))
def mysql_failover_drill_v1_task():
    """TenDBHA、DBHA v1。每天 9:00 发起。"""
    _run_failover_drill_v1(ClusterType.TenDBHA.value, MysqlFailoverDrillV1Flow, FailoverDrillVersion.V1.value)


@register_periodic_task(run_every=crontab(minute=0, hour=9))
def tendbcluster_failover_drill_v1_task():
    """TenDBCluster、DBHA v1。每天 9:00 发起。"""
    _run_failover_drill_v1(
        ClusterType.TenDBCluster.value, TendbClusterFailoverDrillV1Flow, FailoverDrillVersion.V1.value
    )


@register_periodic_task(run_every=crontab(minute=0, hour="11,13"))
def mysql_failover_drill_v1_retry_task():
    """11:00、13:00 只补 TenDBHA 的 DBHA v1。"""
    _run_failover_drill_v1(ClusterType.TenDBHA.value, MysqlFailoverDrillV1Flow, FailoverDrillVersion.V1.value)


@register_periodic_task(run_every=crontab(minute=0, hour="11,13"))
def tendbcluster_failover_drill_v1_retry_task():
    """11:00、13:00 只补 TenDBCluster 的 DBHA v1。"""
    _run_failover_drill_v1(
        ClusterType.TenDBCluster.value, TendbClusterFailoverDrillV1Flow, FailoverDrillVersion.V1.value
    )


def mysql_failover_drill_v2_task():
    """TenDBHA、DBHA v2 的发起入口。

    现在不进 celery beat。要跑时再加 @register_periodic_task。
    小时不能和 v1 的 9:00、11:00、13:00 重合，否则同一时刻会各申请 4 台机器。
    """
    _run_failover_drill_v1(ClusterType.TenDBHA.value, MysqlFailoverDrillV1Flow, FailoverDrillVersion.V2.value)


def tendbcluster_failover_drill_v2_task():
    """TenDBCluster、DBHA v2 的发起入口。

    现在不进 celery beat。要跑时再加 @register_periodic_task。
    小时不能和 v1 的 9:00、11:00、13:00 重合，否则同一时刻会各申请 4 台机器。
    """
    _run_failover_drill_v1(
        ClusterType.TenDBCluster.value, TendbClusterFailoverDrillV1Flow, FailoverDrillVersion.V2.value
    )


def mysql_failover_drill_v2_retry_task():
    """TenDBHA、DBHA v2 的补跑入口。

    现在不进 celery beat。要跑时再加 @register_periodic_task。
    小时不能和 v1 的 9:00、11:00、13:00 重合，否则同一时刻会各申请 4 台机器。
    """
    _run_failover_drill_v1(ClusterType.TenDBHA.value, MysqlFailoverDrillV1Flow, FailoverDrillVersion.V2.value)


def tendbcluster_failover_drill_v2_retry_task():
    """TenDBCluster、DBHA v2 的补跑入口。

    现在不进 celery beat。要跑时再加 @register_periodic_task。
    小时不能和 v1 的 9:00、11:00、13:00 重合，否则同一时刻会各申请 4 台机器。
    """
    _run_failover_drill_v1(
        ClusterType.TenDBCluster.value, TendbClusterFailoverDrillV1Flow, FailoverDrillVersion.V2.value
    )
