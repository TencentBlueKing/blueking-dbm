# -*- coding: utf-8 -*-
"""DTS 监控配置：介质列表、runtime 字典、按 IP 归并角色。"""
from pathlib import Path

import yaml

from backend import env
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.enums.version_phase import PkgSeries
from backend.flow.consts import MediumEnum
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_MASTER_PORT, MYSQL_DTS_WORKER_PORT
from backend.flow.utils.mysql.dts.package_resolver import resolve_v2_mysql_package

MYSQL_CROND_INSTALL_PATH = "/home/mysql/mysql-crond"
MYSQL_MONITOR_INSTALL_PATH = "/home/mysql/mysql-monitor"
CROND_API_URL = "http://127.0.0.1:9999"
DTS_HEARTBEAT_SCHEDULE = "@every 30s"

_MACHINE_MASTER = MachineType.MYSQL_DTS_MASTER.value
_MACHINE_WORKER = MachineType.MYSQL_DTS_WORKER.value
DTS_MACHINE_TYPES = frozenset(
    {
        MachineType.MYSQL_DTS_MASTER.value,
        MachineType.MYSQL_DTS_WORKER.value,
        MachineType.MYSQL_DTS_COLOCATED.value,
    }
)


def get_dts_monitor_media() -> tuple[list[str], str, str]:
    """只拼 mysql-crond + mysql-monitor 两个 V2 latest 包，不下发整包周边。"""
    crond_pkg = resolve_v2_mysql_package(
        pkg_type=MediumEnum.MySQLCrond.value,
        version_series=PkgSeries.LATEST.value,
    )
    monitor_pkg = resolve_v2_mysql_package(
        pkg_type=MediumEnum.MySQLMonitor.value,
        version_series=PkgSeries.LATEST.value,
    )
    file_list = [
        f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{crond_pkg.path}",
        f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{monitor_pkg.path}",
    ]
    return file_list, Path(crond_pkg.path).name, Path(monitor_pkg.path).name


def render_crond_runtime_yaml(*, ip: str, bk_cloud_id: int) -> str:
    """对齐 crond gen-config 的 runtime.yaml，上报通道来自 BKM_DBM_REPORT。"""
    bkm_dbm_report = SystemSettings.get_setting_value(key="BKM_DBM_REPORT") or {}
    event = bkm_dbm_report.get("event") or {}
    metric = bkm_dbm_report.get("metric") or {}
    data = {
        "ip": ip,
        "port": 9999,
        "bk_cloud_id": bk_cloud_id,
        "bk_monitor_beat": {
            "custom_event": {
                "bk_data_id": int(event.get("data_id") or 0),
                "access_token": event.get("token") or "",
                "report_type": "agent",
                "message_kind": "event",
            },
            "custom_metrics": {
                "bk_data_id": int(metric.get("data_id") or 0),
                "access_token": metric.get("token") or "",
                "report_type": "agent",
                "message_kind": "timeseries",
            },
            "beat_path": env.MYSQL_CROND_BEAT_PATH,
            "agent_address": env.MYSQL_CROND_AGENT_ADDRESS,
        },
        "log": {
            "console": False,
            "log_file_dir": f"{MYSQL_CROND_INSTALL_PATH}/logs",
            "debug": False,
            "source": True,
            "json": True,
        },
        "pid_path": MYSQL_CROND_INSTALL_PATH,
        "jobs_user": "mysql",
        "jobs_config": f"{MYSQL_CROND_INSTALL_PATH}/jobs-config.yaml",
    }
    return yaml.safe_dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def build_monitor_runtime_dict(
    *,
    bk_biz_id: int,
    ip: str,
    port: int,
    machine_type: str,
    cluster_name: str,
    bk_cloud_id: int,
) -> dict:
    """monitor-config_{port}.yaml 字段；不写 auth.mysql，bk_instance_id=0。"""
    return {
        "bk_biz_id": bk_biz_id,
        "ip": ip,
        "port": port,
        "bk_instance_id": 0,
        "cluster_type": ClusterType.MySQLDTS.value,
        "immute_domain": cluster_name,
        "machine_type": machine_type,
        "bk_cloud_id": bk_cloud_id,
        "items_config_file": f"{MYSQL_MONITOR_INSTALL_PATH}/items-config_{port}.yaml",
        "api_url": CROND_API_URL,
        "auth": {},
        "dba_sys_dbs": ["mysql"],
    }


def render_monitor_config_yaml(
    *,
    bk_biz_id: int,
    ip: str,
    port: int,
    machine_type: str,
    cluster_name: str,
    bk_cloud_id: int,
) -> str:
    """monitor-config_{port}.yaml；不写 auth.mysql，bk_instance_id=0。"""
    data = build_monitor_runtime_dict(
        bk_biz_id=bk_biz_id,
        ip=ip,
        port=port,
        machine_type=machine_type,
        cluster_name=cluster_name,
        bk_cloud_id=bk_cloud_id,
    )
    data["log"] = {
        "console": False,
        "log_file_dir": f"{MYSQL_MONITOR_INSTALL_PATH}/logs",
        "debug": False,
        "source": True,
        "json": True,
    }
    data["interact_timeout"] = "2s"
    data["default_schedule"] = "@every 1m"
    return yaml.safe_dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render_items_config_yaml(machine_type: str) -> str:
    """dts-heartbeat 全端；dts-task-status 仅 master，打本机 OpenAPI。"""
    items = [
        {
            "name": "dts-heartbeat",
            "enable": True,
            "schedule": DTS_HEARTBEAT_SCHEDULE,
            "machine_type": [_MACHINE_MASTER, _MACHINE_WORKER],
            "role": [],
        }
    ]
    if machine_type == _MACHINE_MASTER:
        items.append(
            {
                "name": "dts-task-status",
                "enable": True,
                "schedule": DTS_HEARTBEAT_SCHEDULE,
                "machine_type": [_MACHINE_MASTER],
                "role": [],
            }
        )
    return yaml.safe_dump(items, allow_unicode=True, default_flow_style=False, sort_keys=False)


def group_monitor_roles(master_nodes: list[dict], worker_nodes: list[dict]) -> dict[str, dict]:
    """按 IP 归并本机要启用的端口角色（同机可同时有 master+worker）。"""
    by_ip: dict[str, dict] = {}
    for node in master_nodes or []:
        ip = (node or {}).get("ip")
        if not ip:
            continue
        rec = by_ip.setdefault(ip, {"bk_cloud_id": int(node.get("bk_cloud_id") or 0), "roles": []})
        rec["roles"].append({"port": int(node.get("port") or MYSQL_DTS_MASTER_PORT), "machine_type": _MACHINE_MASTER})
    for node in worker_nodes or []:
        ip = (node or {}).get("ip")
        if not ip:
            continue
        rec = by_ip.setdefault(ip, {"bk_cloud_id": int(node.get("bk_cloud_id") or 0), "roles": []})
        rec["roles"].append({"port": int(node.get("port") or MYSQL_DTS_WORKER_PORT), "machine_type": _MACHINE_WORKER})
    return by_ip
