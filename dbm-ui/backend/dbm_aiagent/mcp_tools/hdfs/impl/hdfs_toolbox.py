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
import re
import time
import uuid
from typing import Dict, List, Optional, Sequence, Tuple, Type

from django.core.cache import cache
from django.utils.translation import gettext as _

from backend import env
from backend.components import JobApi
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.dbm_aiagent.mcp_tools.common.impl.job import get_job_exec_status
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.hdfs.impl.cluster_meta import validate_hdfs_cluster
from backend.flow.consts import DBA_ROOT_USER
from backend.utils.string import base64_encode

logger = logging.getLogger("root")

# 只统计 iceberg 仓库：库目录是仓库根目录的一级子目录，表目录是库目录的一级子目录。
ICEBERG_WAREHOUSE_ROOT = "/data/iceberg/warehouse"
# 库列表最多回传的库目录数：超出时只回传按名称排序的前 DB_COUNT_MAX 个，并返回库目录总数。
# 截断在节点上完成，Job 日志行数与库目录总数无关。
DB_COUNT_MAX = 100
# 表列表最多回传的表目录数，规则同 DB_COUNT_MAX。
TABLE_COUNT_MAX = 100
# 数据量统计一次最多的表目录数。
NAMED_TABLE_MAX = 20
# Job 失败时最多回传的错误输出行数
FAIL_OUTPUT_MAX_LINES = 50
# 单张表 du 失败时最多回传的错误输出行数
DU_ERROR_MAX_LINES = 5
# 解析失败时错误信息里附带的输出末尾字符数
FAIL_OUTPUT_TAIL_CHARS = 2000
# hdfs dfs -ls 一个条目的最少列数：权限、副本数、属主、属组、大小、日期、时间、路径
LS_MIN_FIELDS = 8
# hdfs dfs -du 一行的最少列数：逻辑大小、含副本的磁盘占用、路径
DU_MIN_FIELDS = 3
# 缺少 du 结果时错误信息里最多列出的表目录数
MISSING_PATH_SAMPLE_MAX = 5
# 逐个 du 之间留出间隔，避免 Hadoop 2.6 的 getContentSummary 把写请求堵成一段。
DU_GAP_SECONDS = 1
# 作业平台脚本语言：1 表示 shell
SCRIPT_LANGUAGE_SHELL = 1
# 作业平台 Job 超时
JOB_TIMEOUT_SECONDS = 300

# 同一集群同一时刻只允许一个 toolbox 任务：工具最终都会让 NameNode 处理 ls / du
# （getContentSummary），压力落在同一个 NameNode 上，换哪台 DataNode 执行都一样，故按集群加锁。
# key 用 cluster_id 拼 cluster_name，便于在 Redis 中直接认出是哪个集群。
TOOLBOX_LOCK_KEY_TPL = "dbm_aiagent:hdfs_toolbox_lock:{cluster_id}_{cluster_name}"
# 锁与 Job 超时一致：提交成功后不主动释放，到期自动释放；只有提交失败时主动释放。
TOOLBOX_LOCK_TTL_SECONDS = JOB_TIMEOUT_SECONDS
# 任务记录：查询结果时按 job_instance_id 取回任务类型与参数，只接受本工具箱提交过的 Job。
TOOLBOX_TASK_KEY_TPL = "dbm_aiagent:hdfs_toolbox_task:{job_instance_id}"
# 任务记录保留 1 天
TOOLBOX_TASK_TTL_SECONDS = 86400
# 建议的结果查询间隔
TOOLBOX_POLL_INTERVAL_SECONDS = 10

TASK_STATUS_RUNNING = "running"
TASK_STATUS_SUCCEEDED = "succeeded"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_CHOICES = (TASK_STATUS_RUNNING, TASK_STATUS_SUCCEEDED, TASK_STATUS_FAILED)

_PATH_RE = re.compile(r"^/(?:[A-Za-z0-9_.=-]+/)*[A-Za-z0-9_.=-]+$")
_MARK_RE = re.compile(r"^===([A-Z_]+)===(.*)$")
_EXIT_RE = re.compile(r"^===EXIT:(\d+)===$")
_HUMAN_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def validate_hdfs_path(path: str) -> str:
    """只接受绝对路径。字符集收窄到目录名里会出现的符号，避免拼进 shell。"""
    path = (path or "").strip().rstrip("/")
    if not path or path == "/" or not _PATH_RE.match(path):
        raise ValueError(_("HDFS 路径必须是不含空格和 shell 元字符的绝对路径"))
    if any(segment in ("", ".", "..") for segment in path.split("/")[1:]):
        raise ValueError(_("HDFS 路径不能包含 . 或 .. 段"))
    return path


def validate_iceberg_db_dir(path: str) -> str:
    """库目录必须是 iceberg 仓库根目录的一级子目录。"""
    path = validate_hdfs_path(path)
    if len(_iceberg_relative_parts(path)) != 1:
        raise ValueError(_("库目录必须是 {}/<库目录>：{}").format(ICEBERG_WAREHOUSE_ROOT, path))
    return path


def validate_iceberg_table_dir(path: str) -> str:
    """表目录必须是 iceberg 库目录的一级子目录。"""
    path = validate_hdfs_path(path)
    if len(_iceberg_relative_parts(path)) != 2:
        raise ValueError(_("表目录必须是 {}/<库目录>/<表目录>：{}").format(ICEBERG_WAREHOUSE_ROOT, path))
    return path


def _iceberg_relative_parts(path: str) -> List[str]:
    prefix = ICEBERG_WAREHOUSE_ROOT + "/"
    if not path.startswith(prefix):
        raise ValueError(_("只支持 iceberg 目录，路径必须以 {} 开头：{}").format(prefix, path))
    return path.replace(prefix, "", 1).split("/")


def human_bytes(size: Optional[int]) -> str:
    """按 1024 进位，保留两位小数。未知大小返回空字符串。"""
    if size is None:
        return ""
    value = float(size)
    unit_index = 0
    while value >= 1024 and unit_index < len(_HUMAN_UNITS) - 1:
        value /= 1024
        unit_index += 1
    if unit_index == 0:
        return "{} {}".format(int(value), _HUMAN_UNITS[unit_index])
    return "{:.2f} {}".format(value, _HUMAN_UNITS[unit_index])


def size_payload(logical: Optional[int], disk: Optional[int]) -> Dict:
    return {
        "logical_bytes": logical,
        "disk_bytes": disk,
        "logical_human": human_bytes(logical),
        "disk_human": human_bytes(disk),
    }


def parse_ls_output(output: str) -> List[Dict]:
    """解析 hdfs dfs -ls 的一行一个条目。

    前 LS_MIN_FIELDS - 1 列不含空格，只切这么多次，最后一段即完整路径，路径含空格也不会被截断。
    """
    entries = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Found "):
            continue
        if line[0] not in ("d", "-"):
            continue
        parts = line.split(None, LS_MIN_FIELDS - 1)
        if len(parts) < LS_MIN_FIELDS:
            continue
        path = parts[-1].rstrip("/")
        entries.append({"is_dir": line[0] == "d", "path": path, "name": path.split("/")[-1]})
    return entries


def parse_du_lines(output: str) -> List[Dict]:
    """目标环境 hdfs dfs -du 固定输出三列：逻辑大小、含副本的磁盘占用、路径。"""
    rows = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < DU_MIN_FIELDS or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        rows.append({"logical_bytes": int(parts[0]), "disk_bytes": int(parts[1]), "path": parts[-1].rstrip("/")})
    return rows


def parse_marked_output(output: str) -> List[Tuple[str, str, str]]:
    """拆出脚本打的分段。退出码非 0 或缺失时直接失败，避免把命令错误当成没有数据。

    Job 超时被作业平台终止时，脚本来不及打印退出码，同样按失败处理。
    """
    sections: List[Tuple[str, str, str]] = []
    exit_code = None
    key = None
    payload = ""
    body: List[str] = []

    def flush():
        nonlocal key, payload, body
        if key is not None:
            sections.append((key, payload, "\n".join(body).strip("\n")))
        key = None
        payload = ""
        body = []

    for line in output.splitlines():
        stripped = line.strip()
        exit_match = _EXIT_RE.match(stripped)
        if exit_match:
            flush()
            exit_code = int(exit_match.group(1))
            continue
        mark = _MARK_RE.match(stripped)
        if mark:
            flush()
            key = mark.group(1)
            payload = mark.group(2)
            body = []
            continue
        if key is not None:
            body.append(line)
    flush()
    tail = output[-FAIL_OUTPUT_TAIL_CHARS:]
    if exit_code is None:
        raise DBMMcpBaseException(msg=_("HDFS 命令没有返回退出码（可能执行超时），输出：{}").format(tail))
    if exit_code != 0:
        raise DBMMcpBaseException(msg=_("HDFS 命令执行失败，退出码 {}，输出：{}").format(exit_code, tail))
    return sections


class HdfsToolboxTask:
    """toolbox 任务：生成节点脚本、解析 Job 日志。

    新增一个 toolbox 功能只需实现一个子类并加入 TOOLBOX_TASKS。
    构造函数负责校验参数；params() 返回的字典必须能原样传回构造函数，用于查询结果时重建任务。
    """

    task_type = ""

    def task_name(self) -> str:
        raise NotImplementedError

    def params(self) -> Dict:
        return {}

    def build_script(self) -> str:
        raise NotImplementedError

    def parse(self, sections: Sequence[Tuple[str, str, str]]) -> Dict:
        raise NotImplementedError


class ListIcebergDbsTask(HdfsToolboxTask):
    """列出 iceberg 仓库下的库目录，最多回传按名称排序的前 DB_COUNT_MAX 个。"""

    task_type = "list_iceberg_dbs"

    def task_name(self) -> str:
        return _("HDFS: 列出 iceberg 库目录")

    def build_script(self) -> str:
        return _build_list_dirs_script(ICEBERG_WAREHOUSE_ROOT, DB_COUNT_MAX)

    def parse(self, sections: Sequence[Tuple[str, str, str]]) -> Dict:
        db_dirs, db_total = _parse_dir_listing(sections)
        truncated = db_total > len(db_dirs)
        message = ""
        if truncated:
            message = _("iceberg 仓库下共 {} 个库目录，只返回按名称排序的前 {} 个；其余库请直接按库目录名指定").format(db_total, DB_COUNT_MAX)
        return {
            "warehouse_dir": ICEBERG_WAREHOUSE_ROOT,
            "db_count": db_total,
            "truncated": truncated,
            "message": message,
            "db_dirs": db_dirs,
        }


class ListIcebergTablesTask(HdfsToolboxTask):
    """列出单个库目录下的表目录，最多回传按名称排序的前 TABLE_COUNT_MAX 个。"""

    task_type = "list_iceberg_tables"

    def __init__(self, db_dir: str):
        self.db_dir = _validate_param(validate_iceberg_db_dir, db_dir)

    def task_name(self) -> str:
        return _("HDFS: 列出 iceberg 表目录")

    def params(self) -> Dict:
        return {"db_dir": self.db_dir}

    def build_script(self) -> str:
        return _build_list_dirs_script(self.db_dir, TABLE_COUNT_MAX)

    def parse(self, sections: Sequence[Tuple[str, str, str]]) -> Dict:
        table_dirs, table_total = _parse_dir_listing(sections)
        truncated = table_total > len(table_dirs)
        message = ""
        if truncated:
            message = _("库 {} 下共 {} 个表目录，只返回按名称排序的前 {} 个；其余表请直接按表目录名指定").format(
                self.db_dir, table_total, TABLE_COUNT_MAX
            )
        return {
            "db_dir": self.db_dir,
            "table_count": table_total,
            "truncated": truncated,
            "message": message,
            "table_dirs": table_dirs,
        }


class IcebergTableSizesTask(HdfsToolboxTask):
    """统计指定表目录（最多 NAMED_TABLE_MAX 个）的数据量：逐表 du -s，每次之间 sleep。

    单张表 du 失败不影响其余表：成功的进 tables，失败的进 failed_tables。
    """

    task_type = "get_iceberg_table_sizes"

    def __init__(self, table_dirs: Sequence[str]):
        paths: List[str] = []
        for path in table_dirs or []:
            value = _validate_param(validate_iceberg_table_dir, path)
            if value not in paths:
                paths.append(value)
        if not paths:
            raise DBMMcpBaseException(msg=_("至少指定一个表目录"))
        if len(paths) > NAMED_TABLE_MAX:
            raise DBMMcpBaseException(msg=_("一次最多指定 {} 个表目录，当前 {} 个").format(NAMED_TABLE_MAX, len(paths)))
        self.table_dirs = paths

    def task_name(self) -> str:
        return _("HDFS: 统计 iceberg 表目录数据量")

    def params(self) -> Dict:
        return {"table_dirs": list(self.table_dirs)}

    def build_script(self) -> str:
        return _build_du_script(self.table_dirs)

    def parse(self, sections: Sequence[Tuple[str, str, str]]) -> Dict:
        sizes: Dict[str, Dict] = {}
        errors: Dict[str, str] = {}
        for key, payload, body in sections:
            if key == "DUERR":
                errors[payload] = body.strip() or _("du 执行失败，无错误输出")
            elif key == "DU":
                rows = parse_du_lines(body)
                if rows:
                    sizes[payload] = rows[0]
                else:
                    errors[payload] = _("du 没有返回可解析的结果：{}").format(body.strip())
        # 每张表都应有成功或失败记录；两者都没有说明输出不完整，整体判失败
        missing = [path for path in self.table_dirs if path not in sizes and path not in errors]
        if missing:
            raise DBMMcpBaseException(
                msg=_("没有拿到 {} 个表目录的 du 记录（输出不完整），例如：{}").format(
                    len(missing), ", ".join(missing[:MISSING_PATH_SAMPLE_MAX])
                )
            )
        tables = [
            {
                "path": path,
                "name": path.split("/")[-1],
                "db_dir": path.rsplit("/", 1)[0],
                **size_payload(sizes[path]["logical_bytes"], sizes[path]["disk_bytes"]),
            }
            for path in self.table_dirs
            if path in sizes
        ]
        failed_tables = [{"path": path, "error": errors[path]} for path in self.table_dirs if path not in sizes]
        return {
            "table_count": len(tables),
            "tables": tables,
            "failed_count": len(failed_tables),
            "failed_tables": failed_tables,
        }


TOOLBOX_TASKS: Dict[str, Type[HdfsToolboxTask]] = {
    task_cls.task_type: task_cls for task_cls in (ListIcebergDbsTask, ListIcebergTablesTask, IcebergTableSizesTask)
}


def submit_task(immute_domain: str, task: HdfsToolboxTask) -> Dict:
    """加集群锁后提交 Job，立即返回 job_instance_id，不等待执行结果。

    提交失败时释放锁；提交成功后锁保持到 TOOLBOX_LOCK_TTL_SECONDS 到期。
    """
    script = task.build_script()
    target = _resolve_execution_target(immute_domain)
    lock_key, token = _acquire_cluster_lock(target)
    try:
        job_instance_id = _submit_job(target, script, task.task_name())
    except Exception:
        _release_cluster_lock(lock_key, token)
        raise
    _save_task_record(
        job_instance_id,
        {
            "task_type": task.task_type,
            "params": task.params(),
            "cluster_id": target["cluster_id"],
            "cluster_domain": immute_domain,
            "submitted_at": int(time.time()),
        },
    )
    return {
        "cluster_domain": immute_domain,
        "task_type": task.task_type,
        "job_instance_id": job_instance_id,
        "poll_interval_seconds": TOOLBOX_POLL_INTERVAL_SECONDS,
        "message": _("任务已提交，请间隔 {} 秒后用 hdfs_toolbox_query_result 查询结果").format(TOOLBOX_POLL_INTERVAL_SECONDS),
    }


def query_task_result(immute_domain: str, job_instance_id: int) -> Dict:
    """查询 toolbox 任务结果，立即返回：未完成为 running；完成后按任务类型解析为 succeeded 或 failed。

    只接受本工具箱提交且属于该集群的 job_instance_id。
    """
    record = _load_task_record(job_instance_id)
    if record["cluster_domain"] != immute_domain:
        raise DBMMcpBaseException(msg=_("任务 {} 不属于集群 {}").format(job_instance_id, immute_domain))
    task_cls = TOOLBOX_TASKS.get(record["task_type"])
    if task_cls is None:
        raise DBMMcpBaseException(msg=_("未知的 HDFS 工具箱任务类型：{}").format(record["task_type"]))
    task = task_cls(**record["params"])
    result = {
        "cluster_domain": immute_domain,
        "job_instance_id": job_instance_id,
        "task_type": task.task_type,
        "status": TASK_STATUS_RUNNING,
        "elapsed_seconds": max(0, int(time.time()) - record["submitted_at"]),
        "message": "",
        "result": None,
    }
    job_resp = get_job_exec_status(job_instance_id)
    if not job_resp["finished"]:
        result["message"] = _("任务执行中，请间隔 {} 秒后再查询").format(TOOLBOX_POLL_INTERVAL_SECONDS)
        return result
    output = "\n".join(entry["log_content"] for entry in job_resp["job_log_resp"] if entry.get("log_content"))
    try:
        payload = task.parse(parse_marked_output(output))
    except DBMMcpBaseException as err:
        result.update(status=TASK_STATUS_FAILED, message=str(err.message))
        return result
    result.update(status=TASK_STATUS_SUCCEEDED, result=payload)
    return result


def _validate_param(validator, value: str) -> str:
    try:
        return validator(value)
    except ValueError as err:
        raise DBMMcpBaseException(msg=str(err))


def _parse_dir_listing(sections: Sequence[Tuple[str, str, str]]) -> Tuple[List[str], int]:
    """节点上 awk 只回传前 max 个目录条目和目录总数，目录下的文件不计入。"""
    entries = parse_ls_output(_section_body(sections, "LS") or "")
    return sorted(entry["path"] for entry in entries if entry["is_dir"]), _section_int(sections, "TOTAL")


def _section_body(sections: Sequence[Tuple[str, str, str]], key: str) -> Optional[str]:
    for section_key, _payload, body in sections:
        if section_key == key:
            return body
    return None


def _section_int(sections: Sequence[Tuple[str, str, str]], key: str) -> int:
    for section_key, payload, _body in sections:
        if section_key == key and payload.strip().isdigit():
            return int(payload.strip())
    raise DBMMcpBaseException(msg=_("HDFS ls 没有返回 {} 计数").format(key))


def _resolve_execution_target(immute_domain: str) -> Dict:
    """取集群中一台 status=running 的 DataNode 作为执行机。"""
    cluster = validate_hdfs_cluster(immute_domain)
    datanode = (
        cluster.storageinstance_set.filter(
            instance_role=InstanceRole.HDFS_DATA_NODE.value, status=InstanceStatus.RUNNING.value
        )
        .select_related("machine")
        .first()
    )
    if not datanode:
        raise DBMMcpBaseException(msg=_("集群 {} 没有状态为 running 的 DataNode").format(immute_domain))
    return {
        "datanode_ip": datanode.machine.ip,
        "bk_cloud_id": cluster.bk_cloud_id,
        "cluster_id": cluster.id,
        "cluster_name": cluster.name,
    }


def _acquire_cluster_lock(target: Dict) -> Tuple[str, str]:
    """集群级 toolbox 互斥锁：同一集群已有 toolbox 任务时直接拒绝，不排队等待。

    - 用 cache.add 实现「不存在才写入」的原子加锁，后端为项目默认 Redis；
    - 值写入本次请求独有的 token，释放时只删自己加的锁；
    - Redis 不可用时拒绝执行（fail-closed）：宁可工具暂不可用，也不在失去并发保护的情况下对 NameNode 发起命令。
    """
    key = TOOLBOX_LOCK_KEY_TPL.format(cluster_id=target["cluster_id"], cluster_name=target["cluster_name"])
    token = uuid.uuid4().hex
    try:
        acquired = cache.add(key, token, timeout=TOOLBOX_LOCK_TTL_SECONDS)
    except Exception as err:  # noqa: BLE001 - 缓存异常统一转成可读错误
        logger.warning("hdfs toolbox lock unavailable, key=%s, err=%s", key, err)
        raise DBMMcpBaseException(msg=_("HDFS 工具箱并发锁暂不可用，为保护 NameNode 本次不执行，请稍后重试"))
    if not acquired:
        raise DBMMcpBaseException(
            msg=_("集群 {} 已有 HDFS 工具箱任务，为避免叠加 NameNode 压力，请在 {} 秒内稍后再试").format(
                target["cluster_name"], TOOLBOX_LOCK_TTL_SECONDS
            )
        )
    return key, token


def _release_cluster_lock(key: str, token: str) -> None:
    try:
        # get 与 delete 之间不是原子操作，只在提交失败时执行一次，窗口极小
        if cache.get(key) == token:
            cache.delete(key)
    except Exception as err:  # noqa: BLE001 - 释放失败由 TTL 兜底
        logger.warning("hdfs toolbox lock release failed, key=%s, err=%s", key, err)


def _save_task_record(job_instance_id: int, record: Dict) -> None:
    key = TOOLBOX_TASK_KEY_TPL.format(job_instance_id=job_instance_id)
    try:
        cache.set(key, record, timeout=TOOLBOX_TASK_TTL_SECONDS)
    except Exception as err:  # noqa: BLE001 - 缓存异常统一转成可读错误
        logger.warning("hdfs toolbox task record save failed, key=%s, err=%s", key, err)
        raise DBMMcpBaseException(
            msg=_("Job {} 已提交，但任务记录保存失败，无法查询结果；集群锁将在 {} 秒后自动释放").format(job_instance_id, TOOLBOX_LOCK_TTL_SECONDS)
        )


def _load_task_record(job_instance_id: int) -> Dict:
    key = TOOLBOX_TASK_KEY_TPL.format(job_instance_id=job_instance_id)
    try:
        record = cache.get(key)
    except Exception as err:  # noqa: BLE001 - 缓存异常统一转成可读错误
        logger.warning("hdfs toolbox task record load failed, key=%s, err=%s", key, err)
        raise DBMMcpBaseException(msg=_("HDFS 工具箱任务记录暂不可读，请稍后重试"))
    if not record:
        raise DBMMcpBaseException(msg=_("任务 {} 不存在或已过期：只能查询 HDFS 工具箱提交的任务").format(job_instance_id))
    return record


def _submit_job(target: Dict, script: str, task_name: str) -> int:
    """以 root 执行，目标环境 root 拥有全部 HDFS 目录权限。只提交，不等待。"""
    body = {
        "account_alias": DBA_ROOT_USER,
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "task_name": str(task_name),
        "script_content": base64_encode(script),
        "script_language": SCRIPT_LANGUAGE_SHELL,
        "target_server": {"ip_list": [{"ip": target["datanode_ip"], "bk_cloud_id": target["bk_cloud_id"]}]},
        "timeout": JOB_TIMEOUT_SECONDS,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)
    return job_task["job_instance_id"]


def _script_header() -> str:
    # Job 平台执行脚本时会加载 HDFS 环境变量，目标机可直接使用 hdfs 命令，
    # 无需在脚本内再次显式加载 /data/hadoopenv/hdfsProfile。
    return """#!/bin/bash
filter_noise() { grep -v '^SLF4J' | grep -v 'NativeCodeLoader' || true; }
"""


def _fail_block(output_var: str) -> str:
    """命令失败时回传错误输出：去掉 ls 列表行，最多 FAIL_OUTPUT_MAX_LINES 行。"""
    return (
        "{\n"
        "  printf '%s\\n' \"$" + output_var + "\" | filter_noise | grep -v '^[d-][rwxsStT-]\\{9\\}' "
        "| head -n " + str(FAIL_OUTPUT_MAX_LINES) + "\n"
        '  echo "===EXIT:1==="\n'
        "  exit 0\n"
        "}"
    )


# ls 的输出交给 awk：只打印前 max 个目录条目，最后打印目录总数。
_DIR_LIST_AWK = r"""BEGIN { print "===LS===" }
/^d/ && NF >= min_fields { n++; if (n <= max) print }
END { print "===TOTAL===" n + 0 }"""


def _build_list_dirs_script(path: str, max_lines: int) -> str:
    """一条 hdfs dfs -ls，输出在节点上交给 awk 收敛后再回传。"""
    return (
        _script_header()
        + "ls_out=$(hdfs dfs -ls "
        + _shell_quote(path)
        + " 2>&1) || "
        + _fail_block("ls_out")
        + "\nprintf '%s\\n' \"$ls_out\" | filter_noise | awk -v max={} -v min_fields={} '".format(
            int(max_lines), LS_MIN_FIELDS
        )
        + _DIR_LIST_AWK
        + "'\n"
        + 'echo "===EXIT:0==="\n'
    )


def _build_du_script(paths: Sequence[str]) -> str:
    """逐个表目录 du -s，每次之间 sleep。

    单张表失败时打 DUERR 段（最多 DU_ERROR_MAX_LINES 行错误输出）后继续下一张；
    全部跑完才打 EXIT:0，Job 超时被终止时缺少该标记，整体判失败。
    """
    lines = [_script_header()]
    for path in paths:
        lines.append(
            """
if du_out=$(hdfs dfs -du -s {quoted} 2>&1); then
  echo "===DU==={raw}"
  printf '%s\\n' "$du_out" | filter_noise
else
  echo "===DUERR==={raw}"
  printf '%s\\n' "$du_out" | filter_noise | head -n {err_lines}
fi
sleep {gap}
""".format(
                raw=path,
                quoted=_shell_quote(path),
                gap=DU_GAP_SECONDS,
                err_lines=DU_ERROR_MAX_LINES,
            )
        )
    lines.append('echo "===EXIT:0==="\n')
    return "".join(lines)


def _shell_quote(value: str) -> str:
    if not _PATH_RE.match(value):
        raise DBMMcpBaseException(msg=_("拒绝把未校验的参数写入 HDFS 命令：{}").format(value))
    return "'{}'".format(value)
