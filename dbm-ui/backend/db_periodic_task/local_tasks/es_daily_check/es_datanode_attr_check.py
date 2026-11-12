import logging
import time
from typing import Dict, List, Optional, Tuple

from backend import env
from backend.components import JobApi
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import AppCache, Cluster, Machine, StorageInstance
from backend.db_report.enums import ReportStateType
from backend.db_report.models import EsDatanodeAttrReport
from backend.flow.consts import DBA_ROOT_USER
from backend.utils.string import base64_encode

logger = logging.getLogger("celery")

JOB_POLL_INTERVAL = 5
JOB_POLL_MAX_RETRIES = 60
ES_ATTR_SENTINEL = "ES_DATANODE_ATTR"
NODE_ROLE_MAP = {
    InstanceRole.ES_DATANODE_HOT.value: "hot",
    InstanceRole.ES_DATANODE_COLD.value: "cold",
}
VALID_NODE_ROLES = {"hot", "cold"}
BKJOB_HOST_SUCCESS_STATUS = 9
BKJOB_HOST_SUCCESS_ERROR_CODES = {0, 9}
ES_ATTR_COLLECT_SCRIPT = """#!/bin/sh
normalize_value() {
    echo "$1" | sed \
        -e 's/[[:space:]]*#.*$//' \
        -e 's/^[[:space:]]*//' \
        -e 's/[[:space:]]*$//' \
        -e 's/^"//' \
        -e 's/"$//' \
        -e "s/^'//" \
        -e "s/'$//"
}

get_conf_value() {
    direct_key="$1"
    node_nested_key="$2"
    attr_nested_key="$3"
    conf="$4"
    value=$(awk -v direct_key="$direct_key" -v node_nested_key="$node_nested_key" -v attr_nested_key="$attr_nested_key" '
function strip_comment(s) {
    sub(/[[:space:]]*#.*$/, "", s)
    return s
}
function ltrim(s) {
    sub(/^[[:space:]]+/, "", s)
    return s
}
function rtrim(s) {
    sub(/[[:space:]]+$/, "", s)
    return s
}
function trim(s) {
    return rtrim(ltrim(s))
}
function indent_len(s) {
    match(s, /[^[:space:]]/)
    if (RSTART == 0) {
        return 0
    }
    return RSTART - 1
}
function parse_key_value(line, pos) {
    pos = index(line, ":")
    if (pos == 0) {
        parsed_key = ""
        parsed_value = ""
        return 0
    }
    parsed_key = trim(substr(line, 1, pos - 1))
    parsed_value = trim(substr(line, pos + 1))
    return 1
}
{
    raw = strip_comment($0)
    if (raw ~ /^[[:space:]]*$/) {
        next
    }

    indent = indent_len(raw)
    trimmed = ltrim(raw)

    if (!parse_key_value(trimmed)) {
        next
    }

    key = parsed_key
    value = parsed_value

    if (key == direct_key) {
        direct_value = value
    }

    if (key == "node" && value == "") {
        in_node = 1
        node_indent = indent
        in_attr = 0
        attr_indent = -1
        next
    }

    if (in_node && indent <= node_indent) {
        in_node = 0
        in_attr = 0
    }

    if (!in_node) {
        next
    }

    if (in_attr && indent <= attr_indent) {
        in_attr = 0
    }

    if (key == node_nested_key) {
        node_value = value
    }

    if (key == "attr" && value == "") {
        in_attr = 1
        attr_indent = indent
        next
    }

    if (in_attr && key == attr_nested_key) {
        attr_value = value
    }
}
END {
    if (direct_value != "") {
        print direct_value
    } else if (node_value != "") {
        print node_value
    } else if (attr_value != "") {
        print attr_value
    }
}
' "$conf")
    normalize_value "$value"
}

found=0
for conf in /data/esenv/es_*/config/elasticsearch.yml; do
    [ -f "$conf" ] || continue
    found=1
    node_name=$(get_conf_value 'node.name' 'name' '' "$conf")
    node_tag=$(get_conf_value 'node.attr.tag' 'attr.tag' 'tag' "$conf")
    idc_id=$(get_conf_value 'node.attr.idc_id' 'attr.idc_id' 'idc_id' "$conf")
    rack_id=$(get_conf_value 'node.attr.rack_id' 'attr.rack_id' 'rack_id' "$conf")
    sub_zone_id=$(get_conf_value 'node.attr.sub_zone_id' 'attr.sub_zone_id' 'sub_zone_id' "$conf")
    echo "ES_DATANODE_ATTR|$conf|$node_name|$node_tag|$idc_id|$rack_id|$sub_zone_id"
done

[ "$found" -eq 1 ] || echo "ES_DATANODE_ATTR|NO_FILE"
"""


def _normalize_attr_value(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_machine_map(cluster: Cluster) -> Dict[int, Machine]:
    machines = Machine.objects.filter(
        storageinstance__cluster=cluster,
        storageinstance__instance_role__in=[InstanceRole.ES_DATANODE_HOT, InstanceRole.ES_DATANODE_COLD],
        machine_type=MachineType.ES_DATANODE,
    ).distinct()
    return {machine.bk_host_id: machine for machine in machines}


def _build_role_map(cluster: Cluster) -> Dict[int, str]:
    role_map = {}
    instances = StorageInstance.objects.filter(
        cluster=cluster,
        instance_role__in=[InstanceRole.ES_DATANODE_HOT, InstanceRole.ES_DATANODE_COLD],
    ).select_related("machine")
    for instance in instances:
        role_map[instance.machine.bk_host_id] = NODE_ROLE_MAP.get(instance.instance_role, "")
    return role_map


def _build_job_host_error_logs(host_id_list: List[int], failure_msg: str) -> Dict[int, dict]:
    return {
        host_id: {
            "ip": "",
            "bk_cloud_id": None,
            "status": None,
            "error_code": None,
            "exit_code": None,
            "log_content": "",
            "failure_msg": failure_msg,
        }
        for host_id in host_id_list
    }


def _fetch_job_host_logs(job_instance_id: int, target_host_id_list: List[int]):
    try:
        status_resp = JobApi.get_job_instance_status(
            {
                "bk_scope_type": "biz_set",
                "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
                "job_instance_id": job_instance_id,
                "return_ip_result": True,
            },
            use_admin=True,
        )
    except Exception as e:
        # 网络抖动等瞬时错误允许轮询重试，不要把一次调用失败升级为整个集群采集失败
        logger.warning(
            "get_job_instance_status transient error, job_instance_id=%s, err=%s",
            job_instance_id,
            e,
        )
        return None

    if not status_resp.get("finished"):
        return None

    step_instance_list = status_resp.get("step_instance_list") or []
    if not step_instance_list:
        return _build_job_host_error_logs(target_host_id_list, "bkjob未返回步骤结果，无法校验 elasticsearch.yml")

    step_instance = step_instance_list[0]
    step_instance_id = step_instance.get("step_instance_id")
    ip_result_list = step_instance.get("step_ip_result_list") or []
    if not step_instance_id or not ip_result_list:
        return _build_job_host_error_logs(target_host_id_list, "bkjob未返回主机执行结果，无法校验 elasticsearch.yml")

    host_logs = {
        res["bk_host_id"]: {
            "ip": res.get("ip", ""),
            "bk_cloud_id": res.get("bk_cloud_id"),
            "status": res.get("status"),
            "error_code": res.get("error_code"),
            "exit_code": res.get("exit_code"),
            "log_content": "",
        }
        for res in ip_result_list
        if res.get("bk_host_id") is not None
    }

    try:
        log_resp = JobApi.batch_get_job_instance_ip_log(
            {
                "bk_scope_type": "biz_set",
                "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
                "job_instance_id": job_instance_id,
                "step_instance_id": step_instance_id,
                "host_id_list": list(host_logs.keys()),
            },
            use_admin=True,
        )
    except Exception as e:
        logger.warning(
            "batch_get_job_instance_ip_log failed, job_instance_id=%s, err=%s",
            job_instance_id,
            e,
        )
        log_resp = {}

    for log in log_resp.get("script_task_logs") or []:
        host_id = log.get("host_id")
        if host_id in host_logs:
            host_logs[host_id].update(
                {
                    "log_content": log.get("log_content", ""),
                    "status": log.get("status", host_logs[host_id].get("status")),
                    "error_code": log.get("error_code", host_logs[host_id].get("error_code")),
                    "exit_code": log.get("exit_code", host_logs[host_id].get("exit_code")),
                }
            )

    missing_host_ids = [host_id for host_id in target_host_id_list if host_id not in host_logs]
    if missing_host_ids:
        host_logs.update(_build_job_host_error_logs(missing_host_ids, "bkjob未返回主机执行结果，无法校验 elasticsearch.yml"))

    return host_logs


def _exec_es_attr_collect_script(host_id_list: List[int], cluster_domain: str) -> Dict[int, dict]:
    logger.info(
        "start bkjob collect es datanode attrs for cluster %s, host_count=%s",
        cluster_domain,
        len(host_id_list),
    )
    body = {
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "account_alias": DBA_ROOT_USER,
        "task_name": "DBM 采集 ES 数据节点 elasticsearch.yml 拓扑属性",
        "script_content": base64_encode(ES_ATTR_COLLECT_SCRIPT),
        "script_language": 1,
        "target_server": {"host_id_list": host_id_list},
        "timeout": 300,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)
    job_instance_id = job_task.get("job_instance_id")
    if not job_instance_id:
        raise Exception(
            "下发 bkjob 采集 ES 数据节点 elasticsearch.yml 失败, cluster: {}, resp: {}".format(cluster_domain, job_task)
        )

    for __ in range(JOB_POLL_MAX_RETRIES):
        host_logs = _fetch_job_host_logs(job_instance_id, host_id_list)
        if host_logs is not None:
            logger.info(
                "finish bkjob collect es datanode attrs for cluster %s, job_instance_id=%s",
                cluster_domain,
                job_instance_id,
            )
            return host_logs
        time.sleep(JOB_POLL_INTERVAL)

    raise Exception(
        "采集 ES 数据节点 elasticsearch.yml 超时, cluster: {}, job_instance_id: {}".format(cluster_domain, job_instance_id)
    )


def _get_es_attr_collect_result(log_content: str) -> Tuple[str, List[dict]]:
    configs = []
    has_sentinel = False
    for line in (log_content or "").splitlines():
        line = line.strip()
        if not line.startswith(ES_ATTR_SENTINEL + "|"):
            continue

        has_sentinel = True
        parts = line.split("|")
        if len(parts) == 2 and parts[1] == "NO_FILE":
            return "no_file", []
        if len(parts) != 7:
            continue

        __, conf_path, node_name, node_tag, idc_id, rack_id, sub_zone_id = parts
        configs.append(
            {
                "conf_path": conf_path,
                "node_name": node_name,
                "node_tag": _normalize_attr_value(node_tag),
                "idc_id": _normalize_attr_value(idc_id),
                "rack_id": _normalize_attr_value(rack_id),
                "sub_zone_id": _normalize_attr_value(sub_zone_id),
            }
        )

    if configs:
        return "ok", configs

    if has_sentinel:
        return "parse_empty", []

    return "no_output", []


def _config_signature(config: dict) -> Tuple[str, str, str, str]:
    return config["node_tag"], config["idc_id"], config["rack_id"], config["sub_zone_id"]


def _format_candidate_configs(configs: List[dict]) -> str:
    return "; ".join(
        "{}(tag={}, idc_id={}, rack_id={}, sub_zone_id={})".format(
            config["conf_path"],
            config["node_tag"] or "-",
            config["idc_id"] or "-",
            config["rack_id"] or "-",
            config["sub_zone_id"] or "-",
        )
        for config in configs
    )


def _select_consistent_config(configs: List[dict], conflict_msg_prefix: str) -> Tuple[Optional[dict], Optional[str]]:
    if not configs:
        return None, None

    if len(configs) == 1:
        return configs[0], None

    if len({_config_signature(config) for config in configs}) == 1:
        return configs[0], None

    return None, "{}: {}".format(conflict_msg_prefix, _format_candidate_configs(configs))


def _select_node_config(configs: List[dict], node_role: str) -> Tuple[Optional[dict], Optional[str]]:
    if not configs:
        return None, None

    role_configs = [config for config in configs if config["node_tag"] == node_role]
    if role_configs:
        return _select_consistent_config(
            role_configs,
            "同一主机多个匹配角色({})的候选配置不一致，无法确定用于校验的配置".format(node_role or "unknown"),
        )

    if len(configs) == 1:
        return configs[0], None

    complete_configs = [
        config for config in configs if config["idc_id"] and config["rack_id"] and config["sub_zone_id"]
    ]
    if complete_configs:
        return _select_consistent_config(
            complete_configs,
            "同一主机多个完整候选配置不一致，无法确定用于校验的配置",
        )

    return None, None


def _is_job_host_success(log_info: dict) -> bool:
    status = log_info.get("status")
    error_code = log_info.get("error_code")
    exit_code = log_info.get("exit_code")

    if status != BKJOB_HOST_SUCCESS_STATUS:
        return False

    if error_code is not None and error_code not in BKJOB_HOST_SUCCESS_ERROR_CODES:
        return False

    return exit_code in (None, 0)


def _build_job_host_fail_msg(log_info: dict) -> str:
    status = log_info.get("status")
    error_code = log_info.get("error_code")
    exit_code = log_info.get("exit_code")

    if log_info.get("failure_msg"):
        return log_info["failure_msg"]

    if status is None and error_code is None and exit_code is None and not log_info.get("log_content"):
        return "bkjob未返回主机执行结果，无法校验 elasticsearch.yml"

    return "bkjob执行失败，无法校验 elasticsearch.yml: status={}, error_code={}, exit_code={}".format(
        status if status is not None else "unknown",
        error_code if error_code is not None else "unknown",
        exit_code if exit_code is not None else "unknown",
    )


def _should_check(node_role: str, config: dict) -> bool:
    if node_role not in VALID_NODE_ROLES:
        return False

    if not (config["idc_id"] and config["rack_id"] and config["sub_zone_id"]):
        return False

    return config["idc_id"] != "1"


def _build_report(cluster: Cluster, app: str, dba, machine: Machine, node_role: str, config: dict):
    es_idc_id = config["idc_id"]
    es_rack_id = config["rack_id"]
    es_sub_zone_id = config["sub_zone_id"]

    meta_idc_id = machine.bk_idc_id or 0
    meta_rack_id = machine.bk_rack_id or 0
    meta_sub_zone_id = machine.bk_sub_zone_id or 0

    mismatch_fields = []
    if es_idc_id != str(meta_idc_id):
        mismatch_fields.append(f"idc_id(es={es_idc_id}, meta={meta_idc_id})")
    if es_rack_id != str(meta_rack_id):
        mismatch_fields.append(f"rack_id(es={es_rack_id}, meta={meta_rack_id})")
    if es_sub_zone_id != str(meta_sub_zone_id):
        mismatch_fields.append(f"sub_zone_id(es={es_sub_zone_id}, meta={meta_sub_zone_id})")

    state = ReportStateType.ABNORMAL if mismatch_fields else ReportStateType.NORMAL
    msg = "配置与元数据一致" if not mismatch_fields else "配置与元数据不一致: {}".format(", ".join(mismatch_fields))

    return EsDatanodeAttrReport(
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=machine.bk_cloud_id,
        state=state,
        cluster_type=ClusterType.Es,
        msg=msg,
        domain=cluster.immute_domain,
        app=app,
        dba=dba,
        ip=machine.ip,
        node_name=config["node_name"],
        node_role=node_role,
        es_idc_id=es_idc_id,
        meta_idc_id=meta_idc_id,
        es_rack_id=es_rack_id,
        meta_rack_id=meta_rack_id,
        es_sub_zone_id=es_sub_zone_id,
        meta_sub_zone_id=meta_sub_zone_id,
    )


def _should_persist_report(report: EsDatanodeAttrReport) -> bool:
    return report.state == ReportStateType.ABNORMAL


def _build_abnormal_report(cluster: Cluster, app: str, dba, machine: Machine, node_role: str, msg: str):
    return EsDatanodeAttrReport(
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=machine.bk_cloud_id,
        state=ReportStateType.ABNORMAL,
        cluster_type=ClusterType.Es,
        msg=msg,
        domain=cluster.immute_domain,
        app=app,
        dba=dba,
        ip=machine.ip,
        node_name="",
        node_role=node_role,
        es_idc_id="",
        meta_idc_id=machine.bk_idc_id or 0,
        es_rack_id="",
        meta_rack_id=machine.bk_rack_id or 0,
        es_sub_zone_id="",
        meta_sub_zone_id=machine.bk_sub_zone_id or 0,
    )


def _collect_cluster_reports(cluster: Cluster):
    app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
    es_dba = DBAdministrator().get_biz_db_type_admins(cluster.bk_biz_id, DBType.Es)
    machine_map = _build_machine_map(cluster)
    if not machine_map:
        return []

    role_map = _build_role_map(cluster)
    host_logs = _exec_es_attr_collect_script(list(machine_map.keys()), cluster.immute_domain)

    reports = []
    for host_id, machine in machine_map.items():
        node_role = role_map.get(host_id, "")
        log_info = host_logs.get(host_id, {})
        if not _is_job_host_success(log_info):
            reports.append(
                _build_abnormal_report(
                    cluster=cluster,
                    app=app,
                    dba=es_dba,
                    machine=machine,
                    node_role=node_role,
                    msg=_build_job_host_fail_msg(log_info),
                )
            )
            continue

        collect_status, configs = _get_es_attr_collect_result(log_info.get("log_content", ""))
        if collect_status == "no_file":
            reports.append(
                _build_abnormal_report(
                    cluster=cluster,
                    app=app,
                    dba=es_dba,
                    machine=machine,
                    node_role=node_role,
                    msg="未找到 elasticsearch.yml，无法校验 node.attr 配置",
                )
            )
            continue

        if collect_status in {"parse_empty", "no_output"}:
            reports.append(
                _build_abnormal_report(
                    cluster=cluster,
                    app=app,
                    dba=es_dba,
                    machine=machine,
                    node_role=node_role,
                    msg="已执行采集脚本，但未解析到任何可用的 elasticsearch.yml 配置",
                )
            )
            continue

        node_config, select_error = _select_node_config(configs, node_role)

        if select_error:
            reports.append(
                _build_abnormal_report(
                    cluster=cluster,
                    app=app,
                    dba=es_dba,
                    machine=machine,
                    node_role=node_role,
                    msg=select_error,
                )
            )
            continue

        if not node_config:
            reports.append(
                _build_abnormal_report(
                    cluster=cluster,
                    app=app,
                    dba=es_dba,
                    machine=machine,
                    node_role=node_role,
                    msg="存在 elasticsearch.yml，但未找到可用于当前节点角色的有效配置",
                )
            )
            logger.warning(
                "cluster %s machine %s has no matched elasticsearch.yml config for role %s",
                cluster.immute_domain,
                machine.ip,
                node_role,
            )
            continue

        if not _should_check(node_role, node_config):
            continue

        report = _build_report(
            cluster=cluster,
            app=app,
            dba=es_dba,
            machine=machine,
            node_role=node_role,
            config=node_config,
        )
        if _should_persist_report(report):
            reports.append(report)

    return reports


def check_es_datanode_attr():
    """
    通过 bkjob 远程读取 ES 数据节点 elasticsearch.yml 中的 node.attr
    并与 db_meta_machine 元数据进行一致性校验
    仅校验同时配置了 idc_id/rack_id/sub_zone_id 且 idc_id != 1 的数据节点
    仅持久化异常巡检报告，正常节点和全正常集群不写入数据库
    对 bkjob 执行失败节点输出异常巡检报告
    对同一主机多个候选配置要求配置一致，否则输出异常巡检报告
    按集群串行下发 bkjob 脚本，当前集群完成后再处理下一个集群
    单个集群异常不阻断后续集群，所有集群处理完成后统一抛出汇总异常
    """
    clusters = Cluster.objects.filter(cluster_type=ClusterType.Es).order_by("bk_biz_id", "id")
    failed_clusters = []
    for cluster in clusters:
        try:
            logger.info("serial dispatch bkjob for es cluster %s", cluster.immute_domain)
            reports = _collect_cluster_reports(cluster)
            if not reports:
                logger.info("cluster %s has no abnormal es datanode attr reports to save", cluster.immute_domain)
                continue

            for report in reports:
                report.save()
        except Exception as e:
            logger.exception("check_es_datanode_attr failed for cluster %s: %s", cluster.immute_domain, e)
            failed_clusters.append("{}: {}".format(cluster.immute_domain, str(e)))
            continue

    if failed_clusters:
        raise Exception("check_es_datanode_attr partial failed, msg:{}".format("; ".join(failed_clusters)))
