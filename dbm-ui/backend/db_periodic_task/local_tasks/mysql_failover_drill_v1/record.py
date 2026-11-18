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
import logging
from datetime import timedelta

from django.utils import timezone

from backend.db_periodic_task.constants import FailoverDrillVersion, failover_drill_has_v2
from backend.db_periodic_task.models import (
    MysqlFailoverDrillV1Config,
    MysqlFailoverDrillV1Dbha,
    MysqlFailoverDrillV1Run,
    MysqlFailoverDrillV1Stage,
)
from backend.flow.consts import StateType

logger = logging.getLogger("flow")

PHASE_RESOURCE_APPLY = "resource_apply"
PHASE_APPLY = "apply"
PHASE_DBHA = "dbha"
PHASE_TEARDOWN = "teardown"
PHASE_RETURN_RESOURCE = "return_resource"
PHASE_DONE = "done"
PHASE_SKIP = "skip"

RESULT_RUNNING = "running"
RESULT_FAILED = "failed"
RESULT_PASSED = "passed"
RESULT_PASSED_WITH_SKIPS = "passed_with_skips"
RESULT_SKIPPED = "skipped"

DBHA_UNKNOWN = "unknown"
DBHA_SWITCHED = "switched"
DBHA_TIMEOUT = "timeout"
DBHA_QUERY_ERROR = "query_error"

STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_IGNORED = "ignored"
STATUS_SKIPPED = "skipped"

_SKIP_REASON = {
    "done": "今天已经成功，不再发起",
    "running": "仍在执行，不再发起",
    "hosts_held": "失败且机器未退回，不再发起",
    "attempt_limit": "已到当天次数，不再发起",
    "switch_off": "DBHA v2 总开关未打开，不再发起",
}

_AUDIT = {"creator": "system", "updater": "system"}


def infer_phase(node_name: str) -> str:
    """用节点名判断它落在演练的哪一段。对不上就留空，不改结果行的当前阶段。"""
    name = node_name or ""
    if any(word in name for word in ("归还资源池", "资源池空闲")):
        return PHASE_RETURN_RESOURCE
    if any(word in name for word in ("iptables", "DBHA", "切换")):
        return PHASE_DBHA
    if "db-actuator" in name or any(word in name for word in ("卸载", "下架", "清理", "删除演练")):
        return PHASE_TEARDOWN
    if any(word in name for word in ("上架", "安装", "介质", "主从", "初始化", "域名", "标准化", "DBMeta", "集群部署")):
        return PHASE_APPLY
    return ""


def locate_node(pipeline: dict, node_id: str, task_ids: set):
    """在流程树里找到节点名，以及它所属城市子流程的 main_task_id。"""

    def walk(node, current_task_id):
        activities = node.get("activities") or {}
        for act in activities.values():
            name = act.get("name") or ""
            found = current_task_id
            for task_id in task_ids:
                if task_id and task_id in name:
                    found = task_id
            if act.get("id") == node_id:
                return found, name
            child = act.get("pipeline")
            if isinstance(child, dict):
                hit = walk(child, found)
                if hit is not None:
                    return hit
        return None

    if not isinstance(pipeline, dict):
        return None, ""
    hit = walk(pipeline, "")
    if hit is None:
        return None, ""
    return hit


def dbha_version_of(version) -> str:
    """配置和结果只记原子版本。含 v2 记 v2，其余记 v1。"""
    if failover_drill_has_v2(version):
        return FailoverDrillVersion.V2.value
    return FailoverDrillVersion.V1.value


def dbha_v2_switch_open(version) -> bool:
    """v1 不看总开关。v2 执行前要 ENABLE_DBHA_V2 打开。"""
    if dbha_version_of(version) != FailoverDrillVersion.V2.value:
        return True
    from backend import env

    return bool(env.ENABLE_DBHA_V2)


def drill_cluster_name(abbr, version) -> str:
    """v2 域名带版本，避免和同一城市的 v1 演练抢同一个域名。"""
    name = "failover-drill-{}".format((abbr or "").strip() or "default")
    if dbha_version_of(version) == FailoverDrillVersion.V2.value:
        return "{}-v2".format(name)
    return name


def _city_version(obj):
    return (obj.city, dbha_version_of(getattr(obj, "version", None)))


def record_skip(conf, reason):
    """这次调度不发起。结果表记一行，不占用当天次数。"""
    from backend.utils.basic import generate_root_id

    message = _SKIP_REASON.get(reason, reason)
    run = MysqlFailoverDrillV1Run.objects.create(
        main_task_id=generate_root_id(),
        bk_biz_id=conf.bk_biz_id,
        bk_cloud_id=conf.bk_cloud_id,
        city=conf.city,
        cluster_type=conf.cluster_type,
        version=dbha_version_of(conf.version),
        labels=conf.labels or [],
        phase=PHASE_SKIP,
        flow_result=RESULT_SKIPPED,
        dbha_result=DBHA_UNKNOWN,
        resource_returned=True,
        finished_at=timezone.now(),
        error_message=message,
        **_AUDIT,
    )
    _append_stage(run, "skip", STATUS_SKIPPED, PHASE_SKIP, error_message=message, target=conf.city)
    return run


def _actual_runs(runs):
    """跳过行只留档，不参与重试次数和当天是否完成的判断。"""
    return [run for run in runs if getattr(run, "flow_result", "") != RESULT_SKIPPED]


def open_city_run(
    bk_biz_id,
    bk_cloud_id,
    city,
    cluster_type,
    main_task_id,
    labels,
    version=FailoverDrillVersion.V1.value,
):
    return MysqlFailoverDrillV1Run.objects.create(
        main_task_id=main_task_id,
        bk_biz_id=bk_biz_id,
        bk_cloud_id=bk_cloud_id,
        city=city,
        cluster_type=cluster_type,
        version=dbha_version_of(version),
        labels=labels or [],
        phase=PHASE_RESOURCE_APPLY,
        flow_result=RESULT_RUNNING,
        dbha_result=DBHA_UNKNOWN,
        **_AUDIT,
    )


def _append_stage(run, stage, status, phase, error_message="", node_id="", target=""):
    now = timezone.now()
    MysqlFailoverDrillV1Stage.objects.create(
        run=run,
        stage=stage[:255],
        target=(target or "")[:255],
        status=status,
        node_id=(node_id or "")[:64],
        phase=phase,
        error_message=(error_message or "")[:4000],
        finished_at=None if status == STATUS_RUNNING else now,
    )


def finish_resource_apply(run, hosts, master_domain, slave_domain):
    run.hosts = hosts
    run.master_domain = master_domain
    run.slave_domain = slave_domain
    run.phase = PHASE_APPLY
    run.save(update_fields=["hosts", "master_domain", "slave_domain", "phase", "update_at", "updater"])
    _append_stage(run, "resource_apply", STATUS_SUCCEEDED, PHASE_RESOURCE_APPLY, target=run.city)


def fail_resource_apply(run, error_message):
    run.flow_result = RESULT_FAILED
    run.phase = PHASE_RESOURCE_APPLY
    run.error_message = (error_message or "")[:4000]
    run.finished_at = timezone.now()
    run.save(update_fields=["flow_result", "phase", "error_message", "finished_at", "update_at", "updater"])
    _append_stage(
        run,
        "resource_apply",
        STATUS_FAILED,
        PHASE_RESOURCE_APPLY,
        error_message=error_message,
        target=run.city,
    )


def attach_root(main_task_ids, root_id):
    MysqlFailoverDrillV1Run.objects.filter(main_task_id__in=list(main_task_ids)).update(
        root_id=root_id, updater="system", update_at=timezone.now()
    )


def _clip(message) -> str:
    return "{}".format(message or "")[:4000]


def open_dbha_rows(run, drill_ips):
    """按实例类型先占一行。报告节点回来后更新，没跑到报告节点时保持 unknown。"""
    rows = []
    for instance_type, ip in drill_ips.items():
        rows.append(
            MysqlFailoverDrillV1Dbha(
                run=run,
                version=run.version,
                instance_type=instance_type,
                ip=ip or "",
                dbha_result=DBHA_UNKNOWN,
            )
        )
    if rows:
        MysqlFailoverDrillV1Dbha.objects.bulk_create(rows)


def _rollup_dbha_result(results):
    if results and all(result == DBHA_SWITCHED for result in results):
        return DBHA_SWITCHED
    if any(result == DBHA_QUERY_ERROR for result in results):
        return DBHA_QUERY_ERROR
    if results:
        return DBHA_TIMEOUT
    return DBHA_UNKNOWN


def mark_dbha_results(main_task_id, type_results):
    """按实例类型写切换结果。结果行的 dbha_result 是汇总，全部 switched 才是 switched。"""
    run = MysqlFailoverDrillV1Run.objects.filter(main_task_id=main_task_id).first()
    if run is None:
        return
    summaries = []
    for item in type_results:
        instance_type = item["instance_type"]
        dbha_result = item["dbha_result"]
        error_message = _clip(item.get("error_message"))
        MysqlFailoverDrillV1Dbha.objects.update_or_create(
            run=run,
            instance_type=instance_type,
            defaults={
                "version": run.version,
                "ip": item.get("ip") or "",
                "dbha_result": dbha_result,
                "dbha_status": (item.get("dbha_status") or "")[:64],
                "error_message": error_message,
                "switch_start_time": item.get("switch_start_time") or None,
                "switch_finished_time": item.get("switch_finished_time") or None,
            },
        )
        stage_status = STATUS_SUCCEEDED if dbha_result == DBHA_SWITCHED else STATUS_FAILED
        _append_stage(
            run,
            "dbha_report",
            stage_status,
            PHASE_DBHA,
            error_message=error_message or dbha_result,
            target=instance_type,
        )
        summaries.append(dbha_result)
    run.dbha_result = _rollup_dbha_result(summaries)
    run.updater = "system"
    run.save(update_fields=["dbha_result", "updater", "update_at"])


def mark_dbha_result(main_task_id, dbha_result, error_message=""):
    """只有汇总、没有实例类型时使用。没切成功时把原因记到过程表，不把整条 flow 判失败。"""
    run = MysqlFailoverDrillV1Run.objects.filter(main_task_id=main_task_id).first()
    if run is None:
        return
    run.dbha_result = dbha_result
    run.updater = "system"
    run.save(update_fields=["dbha_result", "updater", "update_at"])
    if dbha_result == DBHA_SWITCHED:
        return
    _append_stage(
        run,
        "dbha_report",
        STATUS_FAILED,
        PHASE_DBHA,
        error_message=error_message or dbha_result,
    )


def mark_emergency_return(main_task_id, returned, error_message=""):
    run = MysqlFailoverDrillV1Run.objects.filter(main_task_id=main_task_id).first()
    if run is None:
        return
    message = _clip(error_message).strip()
    if not returned:
        message = "\n".join(part for part in (message, "机器退回资源池失败") if part)
    run.resource_returned = returned
    run.labels_applied = returned
    run.phase = PHASE_RETURN_RESOURCE
    run.flow_result = RESULT_FAILED
    run.error_message = _clip(message)
    run.finished_at = run.finished_at or timezone.now()
    run.save(
        update_fields=[
            "resource_returned",
            "labels_applied",
            "phase",
            "flow_result",
            "error_message",
            "finished_at",
            "update_at",
            "updater",
        ]
    )
    status = STATUS_SUCCEEDED if returned else STATUS_FAILED
    _append_stage(run, "emergency_resource_import", status, PHASE_RETURN_RESOURCE, error_message=message)


def fail_flow_start(main_task_id, error_message):
    """flow.run() 抛错时记下原因。树已经在的，机器仍交给流程里的下架。"""
    run = MysqlFailoverDrillV1Run.objects.filter(main_task_id=main_task_id).first()
    if run is None:
        return
    run.flow_result = RESULT_FAILED
    run.error_message = _clip(error_message)
    run.finished_at = timezone.now()
    run.save(update_fields=["flow_result", "error_message", "finished_at", "update_at", "updater"])
    _append_stage(run, "start_flow", STATUS_FAILED, run.phase or PHASE_APPLY, error_message=error_message)


def _read_node_ex_data(node_id: str) -> str:
    """节点输出里如果已经有失败原因，就拿来记到过程表。"""
    if not node_id:
        return ""
    from pipeline.eri.models import ExecutionData

    row = ExecutionData.objects.filter(node_id=node_id).only("outputs").first()
    if row is None or not row.outputs:
        return ""
    try:
        outputs = json.loads(row.outputs)
    except (TypeError, ValueError):
        return ""
    if not isinstance(outputs, dict):
        return ""
    return _clip(outputs.get("ex_data")).strip()


def _latest_flow_nodes(root_id):
    from backend.flow.models import FlowNode

    chosen = {}
    for node in FlowNode.objects.filter(root_id=root_id).order_by("updated_at", "id"):
        chosen[node.node_id] = node
    return list(chosen.values())


def _stage_status(flow_status: str, node_id: str, ignored_ids: set) -> str:
    if flow_status in (StateType.FAILED.value, StateType.REVOKED.value):
        return STATUS_FAILED
    if flow_status == StateType.RUNNING.value:
        return STATUS_RUNNING
    if flow_status == StateType.FINISHED.value:
        return STATUS_IGNORED if node_id in ignored_ids else STATUS_SUCCEEDED
    return ""


def _upsert_stage(run, node_id, node_name, status, phase, error_message):
    stage = run.stages.filter(node_id=node_id).order_by("-id").first()
    if stage is None:
        _append_stage(run, node_name or node_id, status, phase, error_message=error_message, node_id=node_id)
        return
    stage.stage = (node_name or node_id)[:255]
    stage.status = status
    stage.phase = phase
    if error_message:
        stage.error_message = _clip(error_message)
    if status != STATUS_RUNNING:
        stage.finished_at = stage.finished_at or timezone.now()
    stage.save(update_fields=["stage", "status", "phase", "error_message", "finished_at"])


def sync_run(run):
    """用这座城市的 root_id 读 flow_node，把节点状态写回演练结果。"""
    from pipeline.eri.models import State

    from backend.flow.models import FlowTree

    if not run.root_id:
        return
    tree = FlowTree.objects.filter(root_id=run.root_id).first()
    if tree is None:
        return
    ignored_ids = set(State.objects.filter(root_id=run.root_id, error_ignored=True).values_list("node_id", flat=True))
    task_ids = {run.main_task_id}
    saw_failed = False
    phase = ""
    error_message = ""
    returned = False
    for node in _latest_flow_nodes(run.root_id):
        _, node_name = locate_node(tree.tree or {}, node.node_id, task_ids)
        status = _stage_status(node.status, node.node_id, ignored_ids)
        if not status:
            continue
        node_phase = infer_phase(node_name)
        detail = ""
        if status in (STATUS_FAILED, STATUS_IGNORED):
            detail = _read_node_ex_data(node.node_id) or (node_name or node.node_id)
        _upsert_stage(run, node.node_id, node_name, status, node_phase, detail)
        if node_phase:
            phase = node_phase
        if status == STATUS_FAILED:
            saw_failed = True
            error_message = detail or error_message
        if status == STATUS_SUCCEEDED and node_phase == PHASE_RETURN_RESOURCE and "归还资源池" in (node_name or ""):
            returned = True
    if phase:
        run.phase = phase
    if returned:
        run.resource_returned = True
        run.labels_applied = True
    if saw_failed or tree.status in (StateType.FAILED.value, StateType.REVOKED.value):
        run.flow_result = RESULT_FAILED
        if error_message:
            run.error_message = _clip(error_message)
        if tree.status in (StateType.FAILED.value, StateType.REVOKED.value, StateType.FINISHED.value):
            run.finished_at = run.finished_at or timezone.now()
    elif tree.status == StateType.FINISHED.value:
        _finalize_run(run, city_failed=False)
    run.save(
        update_fields=[
            "phase",
            "flow_result",
            "error_message",
            "resource_returned",
            "labels_applied",
            "finished_at",
            "update_at",
            "updater",
        ]
    )


def sync_run_by_main_task(main_task_id):
    try:
        run = MysqlFailoverDrillV1Run.objects.filter(main_task_id=main_task_id).first()
        if run is not None:
            sync_run(run)
    except Exception:
        logger.exception("sync failover drill v1 run failed: main_task_id=%s", main_task_id)


def sync_running_runs():
    """只扫还在跑、并且已经有 root_id 的演练行。"""
    runs = MysqlFailoverDrillV1Run.objects.filter(flow_result=RESULT_RUNNING).exclude(root_id="")
    for run in runs:
        try:
            sync_run(run)
        except Exception:
            logger.exception("sync failover drill v1 run failed: root_id=%s", run.root_id)


# 9:00 一次，11:00、13:00 各一次。次数到了就停，15:00 用当天最新结果做总结。
MAX_DAILY_ATTEMPTS = 3


def local_day_window(now=None):
    """项目时区的今天 [00:00, 次日 00:00)。"""
    current = timezone.localtime(now) if now else timezone.localtime()
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _holds_hosts(run) -> bool:
    return bool(getattr(run, "hosts", None)) and not run.resource_returned and run.flow_result == RESULT_FAILED


def _snapshot(run, attempts, reason):
    return {
        "reason": reason,
        "attempts": attempts,
        "phase": getattr(run, "phase", "") or "",
        "flow_result": getattr(run, "flow_result", "") or "",
        "dbha_result": getattr(run, "dbha_result", "") or "",
        "error_message": getattr(run, "error_message", "") or "",
    }


def city_day_status(today_runs, open_runs=None):
    """今天这座城市完成了返回 None。否则返回原因，给重试和告警用。

    open_runs 是跨天还没退机器、或还在跑的记录。今天已经成功就不再看它们。
    """
    today_runs = _actual_runs(today_runs)
    open_runs = _actual_runs(open_runs or [])
    if any(run.flow_result in (RESULT_PASSED, RESULT_PASSED_WITH_SKIPS) for run in today_runs):
        return None
    running = [run for run in list(today_runs) + open_runs if run.flow_result == RESULT_RUNNING]
    if running:
        return _snapshot(running[-1], len(today_runs), "running")
    held = [run for run in list(today_runs) + open_runs if _holds_hosts(run)]
    if held:
        return _snapshot(held[-1], len(today_runs), "hosts_held")
    if not today_runs:
        return _snapshot_empty()
    if len(today_runs) >= MAX_DAILY_ATTEMPTS:
        return _snapshot(today_runs[-1], len(today_runs), "attempt_limit")
    latest = today_runs[-1]
    if latest.flow_result == RESULT_FAILED:
        return _snapshot(latest, len(today_runs), "failed")
    return _snapshot(latest, len(today_runs), "running")


def _snapshot_empty():
    return {
        "reason": "not_started",
        "attempts": 0,
        "phase": "",
        "flow_result": "",
        "dbha_result": "",
        "error_message": "",
    }


def drill_start_decision(today_runs, open_runs=None):
    """返回 (要不要再发起, 原因)。还在跑、机器没退回、今天已成功、次数到了，都不再发起。"""
    status = city_day_status(today_runs, open_runs)
    if status is None:
        return False, "done"
    if status["reason"] in ("failed", "not_started"):
        return True, status["reason"]
    return False, status["reason"]


def _group_runs(runs, key):
    grouped = {}
    for run in runs:
        grouped.setdefault(key(run), []).append(run)
    return grouped


def select_configs_to_start(configs):
    """从已启用配置里挑出今天还可以发起的城市。"""
    configs = list(configs)
    if not configs:
        return [], []
    start, end = local_day_window()
    cities = [conf.city for conf in configs]
    cluster_type = configs[0].cluster_type
    today_runs = MysqlFailoverDrillV1Run.objects.filter(
        cluster_type=cluster_type,
        city__in=cities,
        started_at__gte=start,
        started_at__lt=end,
    ).order_by("id")
    open_runs = MysqlFailoverDrillV1Run.objects.filter(
        cluster_type=cluster_type,
        city__in=cities,
        resource_returned=False,
        flow_result__in=[RESULT_RUNNING, RESULT_FAILED],
    ).order_by("id")
    today_grouped = _group_runs(today_runs, _city_version)
    open_grouped = _group_runs(open_runs, _city_version)
    chosen = []
    skipped = []
    for conf in configs:
        key = _city_version(conf)
        start_it, reason = drill_start_decision(today_grouped.get(key, []), open_grouped.get(key, []))
        if start_it:
            chosen.append(conf)
        else:
            skipped.append((conf, reason))
    return chosen, skipped


def collect_today_summary():
    """每个已启用的城市、集群类型和 DBHA 版本，取今天最后一次结果。"""
    configs = MysqlFailoverDrillV1Config.select_enabled(
        MysqlFailoverDrillV1Config.objects.all().order_by("cluster_type", "id")
    )
    if not configs:
        return []
    start, end = local_day_window()
    today_runs = MysqlFailoverDrillV1Run.objects.filter(started_at__gte=start, started_at__lt=end).order_by("id")
    open_runs = MysqlFailoverDrillV1Run.objects.filter(
        resource_returned=False,
        flow_result__in=[RESULT_RUNNING, RESULT_FAILED],
    ).order_by("id")
    today_grouped = _group_runs(today_runs, lambda run: (run.cluster_type, run.city, dbha_version_of(run.version)))
    open_grouped = _group_runs(open_runs, lambda run: (run.cluster_type, run.city, dbha_version_of(run.version)))
    rows = []
    for conf in configs:
        version = dbha_version_of(conf.version)
        key = (conf.cluster_type, conf.city, version)
        today = _actual_runs(today_grouped.get(key, []))
        status = city_day_status(today, open_grouped.get(key, []))
        if status is None and today:
            status = _snapshot(today[-1], len(today), "done")
        elif status is None:
            status = _snapshot_empty()
        if status["reason"] == "not_started" and not dbha_v2_switch_open(version):
            status["reason"] = "switch_off"
        status["city"] = conf.city
        status["cluster_type"] = conf.cluster_type
        status["version"] = version
        rows.append(status)
    return rows


def _finalize_run(run, city_failed):
    """城市子流程结束时收口。失败停在当前阶段；走完才记 done。"""
    if city_failed:
        run.flow_result = RESULT_FAILED
    elif run.stages.filter(status=STATUS_IGNORED).exists():
        run.flow_result = RESULT_PASSED_WITH_SKIPS
        run.phase = PHASE_DONE
    else:
        run.flow_result = RESULT_PASSED
        run.phase = PHASE_DONE
    run.finished_at = timezone.now()
