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
import base64
import json
import logging
import re
import time
from collections import defaultdict
from shlex import quote
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.utils.translation import gettext as _

from backend import env
from backend.components import JobApi
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import DBA_ROOT_USER
from backend.utils.string import base64_encode

logger = logging.getLogger("root")

JOB_POLL_INTERVAL = 5
JOB_POLL_RESULT_BUFFER = 10

ES_READONLY_METHOD = "GET"
ES_CURL_LOG_PREFIX = "DBM_ES_MCP"
ES_RESPONSE_BEGIN = f"{ES_CURL_LOG_PREFIX}_RESPONSE_BASE64_BEGIN"
ES_RESPONSE_END = f"{ES_CURL_LOG_PREFIX}_RESPONSE_BASE64_END"
ES_STDERR_BEGIN = f"{ES_CURL_LOG_PREFIX}_STDERR_BASE64_BEGIN"
ES_STDERR_END = f"{ES_CURL_LOG_PREFIX}_STDERR_BASE64_END"
ES_RESULT_BEGIN = f"{ES_CURL_LOG_PREFIX}_RESULT_JSON_BEGIN"
ES_RESULT_END = f"{ES_CURL_LOG_PREFIX}_RESULT_JSON_END"
ES_AUTH_USERNAME_ENV = "ES_USERNAME"
ES_AUTH_PASSWORD_ENV = "ES_PASSWORD"
ES_ERROR_TYPE_MISSING_CREDENTIALS = "missing_credentials"
ES_ERROR_TYPE_CURL_EXIT_NONZERO = "curl_exit_nonzero"
ES_ERROR_TYPE_HTTP_ERROR = "http_error"

ES_ROLE_ORDER = [
    InstanceRole.ES_CLIENT.value,
    InstanceRole.ES_DATANODE_HOT.value,
    InstanceRole.ES_DATANODE_COLD.value,
    InstanceRole.ES_MASTER.value,
]

PATH_PATTERN = re.compile(r"^/[A-Za-z0-9_./*,:\-]*$")
READONLY_EXACT_PATHS = {"/", "/_license", "/_remote/info"}
CLUSTER_READONLY_PATTERNS = [
    re.compile(r"^/_cluster/health(?:/[^/]+)?$"),
    re.compile(r"^/_cluster/state(?:/[^/]+){0,2}$"),
    re.compile(r"^/_cluster/settings$"),
    re.compile(r"^/_cluster/pending_tasks$"),
    re.compile(r"^/_cluster/allocation/explain$"),
]
DIAGNOSE_READONLY_PATTERNS = [
    re.compile(r"^/_tasks(?:/[^/]+)?$"),
    re.compile(r"^/_recovery$"),
    re.compile(r"^/[^/]+/_recovery$"),
    re.compile(r"^/_segments$"),
    re.compile(r"^/[^/]+/_segments$"),
    re.compile(r"^/_shard_stores$"),
    re.compile(r"^/[^/]+/_shard_stores$"),
    re.compile(r"^/_settings(?:/[^/]+)?$"),
    re.compile(r"^/[^/]+/_settings(?:/[^/]+)?$"),
    re.compile(r"^/_mapping$"),
    re.compile(r"^/[^/]+/_mapping$"),
    re.compile(r"^/_alias(?:/[^/]+)?$"),
    re.compile(r"^/[^/]+/_alias(?:/[^/]+)?$"),
]
ALL_INDEX_STATS_PATTERN = re.compile(r"^/_stats(?:/[^/]+)?$")
INDEX_STATS_PATTERN = re.compile(r"^/[^/]+/_stats(?:/[^/]+)?$")
QUERY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


class EsReadonlyApiValidationError(ValueError):
    """ES 只读 API 参数校验异常"""


def _normalize_readonly_path(path: str) -> Tuple[str, Dict[str, list]]:
    """校验并规范化 ES 只读 API path，仅允许 GET 型查询接口。"""
    raw_path = (path or "").strip()
    if not raw_path:
        raise EsReadonlyApiValidationError(_("path 不能为空"))
    if not raw_path.startswith("/"):
        raw_path = f"/{raw_path}"

    parsed = urlsplit(raw_path)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise EsReadonlyApiValidationError(_("path 只能是 ES API 相对路径，不允许携带 scheme、host 或 fragment"))

    path_only = parsed.path or "/"
    if any(ch.isspace() for ch in path_only) or "\\" in path_only or ".." in path_only or "//" in path_only:
        raise EsReadonlyApiValidationError(_("path 包含非法字符或路径跳转"))
    if not PATH_PATTERN.match(path_only):
        raise EsReadonlyApiValidationError(_("path 只能包含字母、数字、下划线、点、斜杠、星号、逗号和短横线"))

    if _is_allowed_readonly_path(path_only):
        return path_only, _parse_embedded_query(parsed.query)

    raise EsReadonlyApiValidationError(
        _(
            "仅允许访问只读 GET 接口：/、/_cat、/_cat/*、/_cluster/stats、/_cluster/stats/*、"
            "/_cluster/health、/_cluster/state、/_cluster/settings、/_cluster/pending_tasks、"
            "/_cluster/allocation/explain、/_stats、/_stats/*、/{index}/_stats、/{index}/_stats/*、"
            "/_nodes、/_nodes/*、/_license、/_tasks、/_tasks/{task_id}、/_recovery、/{index}/_recovery、"
            "/_segments、/{index}/_segments、/_shard_stores、/{index}/_shard_stores、"
            "/_settings、/{index}/_settings、/_mapping、/{index}/_mapping、/_alias、/{index}/_alias、/_remote/info"
        )
    )


def _is_allowed_readonly_path(path: str) -> bool:
    """判断 path 是否属于允许的 ES 只读接口范围。"""
    if path in READONLY_EXACT_PATHS:
        return True
    if path == "/_cat" or path.startswith("/_cat/"):
        return True
    if path == "/_cluster/stats" or path.startswith("/_cluster/stats/"):
        return True
    if any(pattern.match(path) for pattern in CLUSTER_READONLY_PATTERNS):
        return True
    if any(pattern.match(path) for pattern in DIAGNOSE_READONLY_PATTERNS):
        return True
    if ALL_INDEX_STATS_PATTERN.match(path) or INDEX_STATS_PATTERN.match(path):
        return True
    if path == "/_nodes" or path.startswith("/_nodes/"):
        return True
    return False


def _parse_embedded_query(query: str) -> Dict[str, list]:
    """解析 path 中自带的 query string。"""
    parsed_query: Dict[str, list] = defaultdict(list)
    for key, value in parse_qsl(query or "", keep_blank_values=True):
        parsed_query[key].append(value)
    return dict(parsed_query)


def _normalize_query_params(
    path: str, embedded_query: Dict[str, list], query_params: Optional[Dict]
) -> Dict[str, list]:
    """规范化 query params，并为 _cat 接口默认使用 JSON 输出。

    显式传入的 query_params 会覆盖 path 中自带 query string 的同名 key。
    注意：query_params 的类型校验已由 Serializer 的 validate_query_params 保证；
    这里仅在 impl 作为内部函数被独立调用时做兜底判断。
    """
    if query_params is None:
        query_params = {}
    elif not isinstance(query_params, dict):
        raise EsReadonlyApiValidationError(_("query_params 必须是 JSON 对象"))

    normalized: Dict[str, list] = defaultdict(list)

    for key, values in (embedded_query or {}).items():
        _append_query_values(normalized, key, values)

    for key, value in query_params.items():
        normalized_key, normalized_values = _normalize_query_values(key, value)
        if normalized_values:
            normalized[normalized_key] = normalized_values
        else:
            normalized.pop(normalized_key, None)

    if path == "/_cat" or path.startswith("/_cat/"):
        lower_keys = {str(key).lower() for key, values in normalized.items() if values}
        if "format" not in lower_keys:
            normalized["format"].append("json")

    return dict(normalized)


def _append_query_values(normalized: Dict[str, list], key, value):
    normalized_key, normalized_values = _normalize_query_values(key, value)
    normalized[normalized_key].extend(normalized_values)


def _normalize_query_values(key, value) -> Tuple[str, list]:
    key = str(key)
    if not QUERY_KEY_PATTERN.match(key):
        raise EsReadonlyApiValidationError(_("query 参数名非法: {key}").format(key=key))

    values = value if isinstance(value, (list, tuple)) else [value]
    return key, [_normalize_query_value(item) for item in values]


def _normalize_query_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"

    text = str(value)
    if len(text) > 512:
        raise EsReadonlyApiValidationError(_("query 参数值过长，请控制在 512 字符以内"))
    if any(ord(ch) < 32 for ch in text):
        raise EsReadonlyApiValidationError(_("query 参数值包含控制字符"))
    return text


def _build_es_url(scheme: str, host: str, port: int, path: str, query_params: Dict[str, list]) -> str:
    query_pairs = []
    for key, values in query_params.items():
        for value in values:
            query_pairs.append((key, value))
    return urlunsplit((scheme, f"{host}:{port}", path, urlencode(query_pairs), ""))


def _select_execute_instance(cluster: Cluster, execute_role: str = "auto") -> StorageInstance:
    """选择用于执行 curl 的 ES 节点，默认优先 client/hot/cold/master 的 running 实例。"""
    if not execute_role or execute_role == "auto":
        role_order = ES_ROLE_ORDER
    elif execute_role in ES_ROLE_ORDER:
        role_order = [execute_role]
    else:
        raise EsReadonlyApiValidationError(
            _("不支持的 execute_role: {role}，可选值: auto, {allowed}").format(
                role=execute_role, allowed=", ".join(ES_ROLE_ORDER)
            )
        )

    base_qs = StorageInstance.objects.filter(cluster=cluster, status=InstanceStatus.RUNNING.value).select_related(
        "machine"
    )
    for role in role_order:
        instance = base_qs.filter(instance_role=role).first()
        if instance:
            return instance

    raise EsReadonlyApiValidationError(_("集群没有可用于执行查询的 running ES 实例"))


def _build_curl_script(url: str, timeout: int, connect_timeout: int, max_response_bytes: int) -> str:
    """构造远程执行脚本。ES 访问固定使用 curl --request GET，并从 ES 节点环境变量读取 Basic Auth。"""
    return "\n".join(
        [
            "#!/bin/sh",
            "set +e",
            f"URL={quote(url)}",
            f"TIMEOUT={int(timeout)}",
            f"CONNECT_TIMEOUT={int(connect_timeout)}",
            f"MAX_RESPONSE_BYTES={int(max_response_bytes)}",
            f"NETRC_MACHINE={quote(urlsplit(url).hostname or '')}",
            "TMP_BODY=$(mktemp /tmp/dbm_es_mcp_body.XXXXXX)",
            "TMP_ERR=$(mktemp /tmp/dbm_es_mcp_err.XXXXXX)",
            "TMP_LIMIT=$(mktemp /tmp/dbm_es_mcp_limit.XXXXXX)",
            "TMP_NETRC=$(mktemp /tmp/dbm_es_mcp_netrc.XXXXXX)",
            "cleanup() {",
            '    rm -f "$TMP_BODY" "$TMP_ERR" "$TMP_LIMIT" "$TMP_NETRC"',
            "}",
            "trap cleanup EXIT",
            'HTTP_STATUS=""',
            "CURL_EXIT_CODE=0",
            'ERROR_TYPE=""',
            "RESULT_OK=false",
            'RESULT_MESSAGE_BASE64=""',
            "RESULT_RESPONSE_TRUNCATED=false",
            "AUTH_ARGS=",
            f'ES_AUTH_USERNAME="${{{ES_AUTH_USERNAME_ENV}:-}}"',
            f'ES_AUTH_PASSWORD="${{{ES_AUTH_PASSWORD_ENV}:-}}"',
            f"unset {ES_AUTH_USERNAME_ENV} {ES_AUTH_PASSWORD_ENV}",
            'if [ -n "$ES_AUTH_USERNAME" ] && [ -n "$ES_AUTH_PASSWORD" ]; then',
            '    chmod 600 "$TMP_NETRC"',
            "    {",
            "        printf 'machine %s\\n' \"$NETRC_MACHINE\"",
            "        printf 'login %s\\n' \"$ES_AUTH_USERNAME\"",
            "        printf 'password %s\\n' \"$ES_AUTH_PASSWORD\"",
            '    } > "$TMP_NETRC"',
            '    AUTH_ARGS="--netrc-file $TMP_NETRC"',
            "else",
            f'    printf "%s" "{ES_AUTH_USERNAME_ENV}/{ES_AUTH_PASSWORD_ENV} 环境变量缺失或不完整，无法进行 ES Basic Auth" > "$TMP_ERR"',
            f'    ERROR_TYPE="{ES_ERROR_TYPE_MISSING_CREDENTIALS}"',
            "    CURL_EXIT_CODE=2",
            "fi",
            'if [ -n "$AUTH_ARGS" ]; then',
            '    HTTP_STATUS=$(curl --silent --show-error --connect-timeout "$CONNECT_TIMEOUT" '
            '--max-time "$TIMEOUT" --request GET -H "Accept: application/json" '
            '--output "$TMP_BODY" --write-out "%{http_code}" $AUTH_ARGS "$URL" 2>"$TMP_ERR")',
            "    CURL_EXIT_CODE=$?",
            '    if [ "$CURL_EXIT_CODE" -ne 0 ]; then',
            f'        ERROR_TYPE="{ES_ERROR_TYPE_CURL_EXIT_NONZERO}"',
            '    elif [ -n "$HTTP_STATUS" ] && [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then',
            "        RESULT_OK=true",
            "    else",
            f'        ERROR_TYPE="{ES_ERROR_TYPE_HTTP_ERROR}"',
            "    fi",
            "fi",
            "RESPONSE_SIZE=$(wc -c < \"$TMP_BODY\" 2>/dev/null | tr -d ' ')",
            'if [ -z "$RESPONSE_SIZE" ]; then RESPONSE_SIZE=0; fi',
            "RESPONSE_TRUNCATED=0",
            'if [ "$RESPONSE_SIZE" -gt "$MAX_RESPONSE_BYTES" ] 2>/dev/null; then',
            '    head -c "$MAX_RESPONSE_BYTES" "$TMP_BODY" > "$TMP_LIMIT"',
            "    RESPONSE_TRUNCATED=1",
            "    RESULT_RESPONSE_TRUNCATED=true",
            "else",
            '    cat "$TMP_BODY" > "$TMP_LIMIT"',
            "fi",
            'if [ -s "$TMP_ERR" ]; then RESULT_MESSAGE_BASE64=$(base64 "$TMP_ERR" | tr -d \'\\n\'); fi',
            f'echo "{ES_CURL_LOG_PREFIX}_HTTP_STATUS=$HTTP_STATUS"',
            f'echo "{ES_CURL_LOG_PREFIX}_CURL_EXIT_CODE=$CURL_EXIT_CODE"',
            f'echo "{ES_CURL_LOG_PREFIX}_RESPONSE_SIZE=$RESPONSE_SIZE"',
            f'echo "{ES_CURL_LOG_PREFIX}_RESPONSE_TRUNCATED=$RESPONSE_TRUNCATED"',
            f'echo "{ES_RESULT_BEGIN}"',
            (
                'printf \'{"ok":%s,"error_type":"%s","message_base64":"%s",'
                '"http_status":"%s","curl_exit_code":%s,'
                '"response_size":%s,"response_truncated":%s}\n\' \\\n'
                '    "$RESULT_OK" "$ERROR_TYPE" "$RESULT_MESSAGE_BASE64" '
                '"$HTTP_STATUS" "$CURL_EXIT_CODE" "$RESPONSE_SIZE" "$RESULT_RESPONSE_TRUNCATED"'
            ),
            f'echo "{ES_RESULT_END}"',
            f'echo "{ES_STDERR_BEGIN}"',
            'if [ -s "$TMP_ERR" ]; then base64 "$TMP_ERR" | tr -d \'\\n\'; fi',
            "echo",
            f'echo "{ES_STDERR_END}"',
            f'echo "{ES_RESPONSE_BEGIN}"',
            'if [ -s "$TMP_LIMIT" ]; then base64 "$TMP_LIMIT" | tr -d \'\\n\'; fi',
            "echo",
            f'echo "{ES_RESPONSE_END}"',
            "exit 0",
        ]
    )


def _execute_script_by_bkjob(
    script: str, target_ip: str, bk_cloud_id: int, timeout: int
) -> Tuple[int, Dict[str, str]]:
    job_timeout = max(timeout + 30, 60)
    body = {
        "bk_scope_type": "biz_set",
        "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
        "account_alias": DBA_ROOT_USER,
        "task_name": _("DBM MCP 查询 ES 只读接口"),
        "script_content": base64_encode(script),
        "script_language": 1,
        "target_server": {"ip_list": [{"ip": target_ip, "bk_cloud_id": bk_cloud_id}]},
        "timeout": job_timeout,
    }
    job_task = JobApi.fast_execute_script(body, use_admin=True)
    job_instance_id = job_task["job_instance_id"]

    poll_deadline = time.monotonic() + job_timeout + JOB_POLL_RESULT_BUFFER
    while time.monotonic() <= poll_deadline:
        ip_logs = _fetch_job_ip_logs(job_instance_id)
        if ip_logs is not None:
            return job_instance_id, ip_logs
        time.sleep(JOB_POLL_INTERVAL)

    raise TimeoutError(_("查询 ES 只读接口超时，job_instance_id: {job_instance_id}").format(job_instance_id=job_instance_id))


def _fetch_job_ip_logs(job_instance_id: int) -> Optional[Dict[str, str]]:
    status_resp = JobApi.get_job_instance_status(
        {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "return_ip_result": True,
        },
        use_admin=True,
    )
    if not status_resp.get("finished"):
        return None

    step_instances = status_resp.get("step_instance_list") or []
    if not step_instances:
        return {}

    step_instance = step_instances[0]
    step_instance_id = step_instance.get("step_instance_id")
    if not step_instance_id:
        logger.warning(
            "fetch ES MCP job ip logs failed: step_instance_id missing, job_instance_id=%s", job_instance_id
        )
        return {}

    ip_result_list = step_instance.get("step_ip_result_list") or []
    host_id_to_ip = {res["bk_host_id"]: res["ip"] for res in ip_result_list if res.get("bk_host_id")}
    if not host_id_to_ip:
        logger.warning(
            "fetch ES MCP job ip logs skipped: no valid bk_host_id in step_ip_result_list, job_instance_id=%s",
            job_instance_id,
        )
        return {}

    log_resp = JobApi.batch_get_job_instance_ip_log(
        {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "step_instance_id": step_instance_id,
            "host_id_list": list(host_id_to_ip.keys()),
        },
        use_admin=True,
    )
    ip_logs: Dict[str, str] = {}
    for log in log_resp.get("script_task_logs") or []:
        ip = log.get("ip") or host_id_to_ip.get(log.get("host_id"))
        if ip:
            ip_logs[ip] = log.get("log_content", "")
    return ip_logs


def _extract_value(log_content: str, key: str) -> Optional[str]:
    match = re.search(rf"^{re.escape(key)}=(.*)$", log_content or "", re.MULTILINE)
    return match.group(1).strip() if match else None


def _extract_block(log_content: str, begin: str, end: str) -> str:
    match = re.search(rf"{re.escape(begin)}\n(.*?)\n{re.escape(end)}", log_content or "", re.DOTALL)
    return match.group(1).strip() if match else ""


def _decode_base64_text(encoded: str) -> str:
    if not encoded:
        return ""
    try:
        return base64.b64decode(encoded).decode("utf-8", errors="replace")
    except Exception as e:  # noqa
        logger.warning("decode ES MCP base64 output failed: %s", str(e))
        return ""


def _parse_result_payload(log_content: str) -> Optional[Dict]:
    payload = _extract_block(log_content, ES_RESULT_BEGIN, ES_RESULT_END)
    if not payload:
        return None

    try:
        result = json.loads(payload)
    except json.JSONDecodeError as e:
        logger.warning("parse ES MCP structured result failed: %s", str(e))
        return None

    if not isinstance(result, dict):
        logger.warning("parse ES MCP structured result failed: payload is not a JSON object")
        return None

    return result


def _parse_job_log(log_content: str) -> Dict:
    result_payload = _parse_result_payload(log_content)
    raw_response = _decode_base64_text(_extract_block(log_content, ES_RESPONSE_BEGIN, ES_RESPONSE_END))
    stderr = _decode_base64_text(_extract_block(log_content, ES_STDERR_BEGIN, ES_STDERR_END))

    if result_payload:
        http_status = _safe_int(result_payload.get("http_status"))
        curl_exit_code = _safe_int(result_payload.get("curl_exit_code"))
        response_size = _safe_int(result_payload.get("response_size"), default=0)
        response_truncated = _safe_bool(result_payload.get("response_truncated"))
        result_ok = _safe_bool(result_payload.get("ok"))
        error_type = str(result_payload.get("error_type") or "")
        result_message = _decode_base64_text(result_payload.get("message_base64") or "")
        marker_missing = False
    else:
        http_status = _safe_int(_extract_value(log_content, f"{ES_CURL_LOG_PREFIX}_HTTP_STATUS"))
        curl_exit_code = _safe_int(_extract_value(log_content, f"{ES_CURL_LOG_PREFIX}_CURL_EXIT_CODE"))
        response_size = _safe_int(_extract_value(log_content, f"{ES_CURL_LOG_PREFIX}_RESPONSE_SIZE"), default=0)
        response_truncated = _extract_value(log_content, f"{ES_CURL_LOG_PREFIX}_RESPONSE_TRUNCATED") == "1"
        result_ok = None
        error_type = ""
        result_message = ""
        marker_missing = curl_exit_code is None or http_status is None

    if not stderr and result_message:
        stderr = result_message

    data = None
    parse_error = ""
    if raw_response:
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            parse_error = str(e)

    return {
        "http_status": http_status,
        "curl_exit_code": curl_exit_code,
        "response_size": response_size,
        "response_truncated": response_truncated,
        "raw_response": raw_response,
        "stderr": stderr,
        "data": data,
        "json_parse_error": parse_error,
        "marker_missing": marker_missing,
        "ok": result_ok,
        "error_type": error_type,
    }


def _safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes"}:
            return True
        if lowered in {"0", "false", "no", ""}:
            return False
    return default


def query_es_readonly_api(
    bk_biz_id: int,
    cluster_domain: str,
    path: str,
    query_params: Optional[Dict] = None,
    scheme: str = "http",
    execute_role: str = "auto",
    timeout: int = 30,
    connect_timeout: int = 5,
    max_response_bytes: int = 1024 * 1024,
) -> Dict:
    """
    通过 bkjob 下发 curl GET 请求查询 ES 只读接口。

    认证方式：远端脚本直接读取 bkjob 进程环境变量 ES_USERNAME/ES_PASSWORD，两者同时存在时使用 Basic Auth；
    任一变量缺失时直接返回认证配置错误，不允许匿名访问 ES。

    当前仅允许访问以下 ES GET 接口范围：
    - /、/_license、/_remote/info
    - /_cat、/_cat/*
    - /_cluster/stats、/_cluster/stats/*
    - /_cluster/health、/_cluster/state、/_cluster/settings、/_cluster/pending_tasks
    - /_cluster/allocation/explain
    - /_stats、/_stats/*、/{index}/_stats、/{index}/_stats/*
    - /_nodes、/_nodes/*
    - /_tasks、/_tasks/{task_id}
    - /_recovery、/{index}/_recovery、/_segments、/{index}/_segments
    - /_shard_stores、/{index}/_shard_stores
    - /_settings、/{index}/_settings、/_mapping、/{index}/_mapping、/_alias、/{index}/_alias

    返回约定：
    - 成功时：success=True，数据在 data/raw_response，不带 error 字段。
    - 失败时：success=False，必定带 error 字段（涵盖：集群/实例不存在、参数校验失败、
      bkjob 执行异常、无法解析作业日志、curl 非 0 或 ES 返回非 2xx 等）。
    """
    try:
        cluster = Cluster.objects.get(
            bk_biz_id=bk_biz_id,
            immute_domain=cluster_domain,
            cluster_type=ClusterType.Es.value,
        )
    except Cluster.DoesNotExist:
        return {"success": False, "error": _("ES 集群不存在: {domain}").format(domain=cluster_domain)}

    try:
        readonly_path, embedded_query = _normalize_readonly_path(path)
        normalized_query_params = _normalize_query_params(readonly_path, embedded_query, query_params)
        execute_instance = _select_execute_instance(cluster, execute_role=execute_role)
    except EsReadonlyApiValidationError as e:
        return {"success": False, "error": str(e)}

    target_host = execute_instance.machine.ip
    bk_cloud_id = execute_instance.machine.bk_cloud_id
    port = execute_instance.port
    if not port:
        return {"success": False, "error": _("ES 实例端口为空，无法发起查询")}

    url = _build_es_url(
        scheme=scheme,
        host=target_host,
        port=port,
        path=readonly_path,
        query_params=normalized_query_params,
    )
    script = _build_curl_script(
        url=url,
        timeout=timeout,
        connect_timeout=connect_timeout,
        max_response_bytes=max_response_bytes,
    )

    result = {
        "cluster_domain": cluster_domain,
        "bk_biz_id": bk_biz_id,
        "cluster_id": cluster.id,
        "method": ES_READONLY_METHOD,
        "path": readonly_path,
        "query_params": normalized_query_params,
        "request_url": url,
        "execute_host": {
            "ip": target_host,
            "bk_cloud_id": bk_cloud_id,
            "bk_host_id": execute_instance.machine.bk_host_id,
            "role": execute_instance.instance_role,
            "port": port,
        },
    }

    try:
        job_instance_id, ip_logs = _execute_script_by_bkjob(
            script=script,
            target_ip=target_host,
            bk_cloud_id=bk_cloud_id,
            timeout=timeout,
        )
    except Exception as e:  # noqa
        logger.exception("query ES readonly api failed, cluster=%s path=%s", cluster_domain, readonly_path)
        result.update({"success": False, "error": str(e)})
        return result

    log_content = ip_logs.get(target_host) or next(iter(ip_logs.values()), "")
    parsed_log = _parse_job_log(log_content)
    success = (
        parsed_log["ok"]
        if parsed_log["ok"] is not None
        else (
            not parsed_log["marker_missing"]
            and parsed_log["curl_exit_code"] == 0
            and parsed_log["http_status"] is not None
            and 200 <= parsed_log["http_status"] < 300
        )
    )

    result.update(
        {
            "job_instance_id": job_instance_id,
            "success": success,
            "http_status": parsed_log["http_status"],
            "curl_exit_code": parsed_log["curl_exit_code"],
            "response_size": parsed_log["response_size"],
            "response_truncated": parsed_log["response_truncated"],
            "data": parsed_log["data"],
            "raw_response": parsed_log["raw_response"],
            "stderr": parsed_log["stderr"],
            "json_parse_error": parsed_log["json_parse_error"],
        }
    )

    if parsed_log["marker_missing"]:
        result["error"] = _("无法解析 bkjob 执行日志，请检查作业输出")
    elif not success:
        if parsed_log["error_type"] == ES_ERROR_TYPE_MISSING_CREDENTIALS:
            result["error"] = parsed_log["stderr"] or _(
                "{username_env} / {password_env} 环境变量缺失或不完整，无法进行 ES Basic Auth"
            ).format(username_env=ES_AUTH_USERNAME_ENV, password_env=ES_AUTH_PASSWORD_ENV)
        elif parsed_log["error_type"]:
            result["error"] = _(
                "ES 只读接口查询失败，error_type={error_type}，curl_exit_code={curl_exit_code}，"
                "http_status={http_status}，stderr={stderr}"
            ).format(
                error_type=parsed_log["error_type"],
                curl_exit_code=parsed_log["curl_exit_code"],
                http_status=parsed_log["http_status"],
                stderr=parsed_log["stderr"],
            )
        else:
            result["error"] = _(
                "ES 只读接口查询失败，curl_exit_code={curl_exit_code}，" "http_status={http_status}，stderr={stderr}"
            ).format(
                curl_exit_code=parsed_log["curl_exit_code"],
                http_status=parsed_log["http_status"],
                stderr=parsed_log["stderr"],
            )

    return result
