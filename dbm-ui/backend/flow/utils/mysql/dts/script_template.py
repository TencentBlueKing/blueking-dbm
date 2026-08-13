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
import shlex

from jinja2.sandbox import SandboxedEnvironment as Environment

from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_MASTER_PORT, MYSQL_DTS_WORKER_PORT

# 介质包布局固定为 dts/{bin,conf,scripts,...}，解到 deploy_path 去掉顶层 dts/ 即可。
#
# 注意：日志文件必须用 dts_node_name（如 dm-master-1），不能用 pipeline 的 node_name。
# SubBuilder.add_act 会把 kwargs["node_name"] 覆盖成中文 act_name（如「启动 Worker」）。

# 后台启动：优先 setsid -f（util-linux 较新）；旧系统不支持 -f 时回退 setsid ... &
_START_DAEMON_HELPER = """
start_daemon() {
  local bin="$1"
  local conf="$2"
  local out="$3"
  if setsid -f true >/dev/null 2>&1; then
    setsid -f "${bin}" -config "${conf}" > "${out}" 2>&1 < /dev/null
  else
    setsid "${bin}" -config "${conf}" > "${out}" 2>&1 < /dev/null &
  fi
}
"""

start_mysql_dts_master_template = (
    """
set -euo pipefail
DEPLOY_PATH="{{deploy_path}}"
PKG_NAME="{{pkg_name}}"
DTS_NODE_NAME="{{dts_node_name}}"
BIN_DIR="${DEPLOY_PATH}/bin"
CONF_DIR="${DEPLOY_PATH}/conf"
LOG_DIR="${DEPLOY_PATH}/log"
PKG_FILE="/data/install/${PKG_NAME}"
OUTPUT_FILE="${LOG_DIR}/${DTS_NODE_NAME}.output"

if [[ -z "${PKG_NAME}" ]]; then
  echo "pkg_name is empty" >&2
  exit 1
fi
if [[ -z "${DTS_NODE_NAME}" ]]; then
  echo "dts_node_name is empty" >&2
  exit 1
fi
if [[ ! -f "${PKG_FILE}" ]]; then
  echo "DTS package not found: ${PKG_FILE}" >&2
  ls -la /data/install/ || true
  exit 1
fi

mkdir -p "${DEPLOY_PATH}" "${CONF_DIR}" "${LOG_DIR}"
if ! tar -zxf "${PKG_FILE}" -C "${DEPLOY_PATH}" --strip-components=1 2>/dev/null; then
  tar -xf "${PKG_FILE}" -C "${DEPLOY_PATH}" --strip-components=1
fi
if [[ ! -f "${BIN_DIR}/dm-master" ]]; then
  echo "dm-master missing after extract, expect ${BIN_DIR}/dm-master" >&2
  ls -la "${DEPLOY_PATH}" "${BIN_DIR}" || true
  exit 1
fi
chmod +x "${BIN_DIR}/dm-master"
"""
    + _START_DAEMON_HELPER
    + """
start_daemon "${BIN_DIR}/dm-master" "${CONF_DIR}/{{config_file}}" "${OUTPUT_FILE}"

LISTEN_PORT="{{listen_port}}"
is_port_listen() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])${port}$"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])${port}$"
  else
    (echo >"/dev/tcp/127.0.0.1/${port}") >/dev/null 2>&1
  fi
}

# 进程在 + master-addr 端口已监听，才视为启动成功（OpenAPI 注册由后续验收组件负责）
ready=0
for _i in $(seq 1 10); do
  if pgrep -f "${BIN_DIR}/dm-master" >/dev/null 2>&1 && is_port_listen "${LISTEN_PORT}"; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "${ready}" -ne 1 ]]; then
  echo "dm-master failed to become ready (process/port ${LISTEN_PORT}):" >&2
  cat "${OUTPUT_FILE}" >&2 || true
  exit 1
fi
echo "started dm-master ${DTS_NODE_NAME} (listen ${LISTEN_PORT})"
"""
)

start_mysql_dts_worker_template = (
    """
set -euo pipefail
DEPLOY_PATH="{{deploy_path}}"
PKG_NAME="{{pkg_name}}"
DTS_NODE_NAME="{{dts_node_name}}"
BIN_DIR="${DEPLOY_PATH}/bin"
CONF_DIR="${DEPLOY_PATH}/conf"
LOG_DIR="${DEPLOY_PATH}/log"
PKG_FILE="/data/install/${PKG_NAME}"
OUTPUT_FILE="${LOG_DIR}/${DTS_NODE_NAME}.output"

if [[ -z "${PKG_NAME}" ]]; then
  echo "pkg_name is empty" >&2
  exit 1
fi
if [[ -z "${DTS_NODE_NAME}" ]]; then
  echo "dts_node_name is empty" >&2
  exit 1
fi
if [[ ! -f "${PKG_FILE}" ]]; then
  echo "DTS package not found: ${PKG_FILE}" >&2
  ls -la /data/install/ || true
  exit 1
fi

mkdir -p "${DEPLOY_PATH}" "${CONF_DIR}" "${LOG_DIR}"
if ! tar -zxf "${PKG_FILE}" -C "${DEPLOY_PATH}" --strip-components=1 2>/dev/null; then
  tar -xf "${PKG_FILE}" -C "${DEPLOY_PATH}" --strip-components=1
fi
if [[ ! -f "${BIN_DIR}/dm-worker" ]]; then
  echo "dm-worker missing after extract, expect ${BIN_DIR}/dm-worker" >&2
  ls -la "${DEPLOY_PATH}" "${BIN_DIR}" || true
  exit 1
fi
chmod +x "${BIN_DIR}/dm-worker"
"""
    + _START_DAEMON_HELPER
    + """
start_daemon "${BIN_DIR}/dm-worker" "${CONF_DIR}/{{config_file}}" "${OUTPUT_FILE}"

LISTEN_PORT="{{listen_port}}"
is_port_listen() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])${port}$"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])${port}$"
  else
    (echo >"/dev/tcp/127.0.0.1/${port}") >/dev/null 2>&1
  fi
}

# 进程在 + worker-addr 端口已监听，才视为启动成功
ready=0
for _i in $(seq 1 10); do
  if pgrep -f "${BIN_DIR}/dm-worker" >/dev/null 2>&1 && is_port_listen "${LISTEN_PORT}"; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "${ready}" -ne 1 ]]; then
  echo "dm-worker failed to become ready (process/port ${LISTEN_PORT}):" >&2
  cat "${OUTPUT_FILE}" >&2 || true
  exit 1
fi
echo "started dm-worker ${DTS_NODE_NAME} (listen ${LISTEN_PORT})"
"""
)

stop_mysql_dts_process_template = """
set -euo pipefail
# 先停 Worker 再停 Master，满足 offline_worker「进程须先离线」约束
pkill -f "{{deploy_path}}/bin/dm-worker" 2>/dev/null || true
pkill -f "{{deploy_path}}/bin/dm-master" 2>/dev/null || true
sleep 1
echo "stopped dts processes under {{deploy_path}}"
"""

clean_mysql_dts_data_dir_template = """
set -euo pipefail
rm -rf "{{deploy_path}}"
echo "cleaned {{deploy_path}}"
"""

push_mysql_dts_config_template = """
set -euo pipefail
CONF_DIR="{{deploy_path}}/conf"
mkdir -p "${CONF_DIR}"
cat > "${CONF_DIR}/{{config_file}}" <<'DTS_CONFIG_EOF'
{{config_content}}
DTS_CONFIG_EOF
echo "wrote ${CONF_DIR}/{{config_file}}"
"""


def _render(template: str, **kwargs) -> str:
    return Environment().from_string(template).render(**kwargs)


def render_push_config_script(deploy_path: str, config_file: str, config_content: str) -> str:
    return _render(
        push_mysql_dts_config_template,
        deploy_path=deploy_path,
        config_file=config_file,
        config_content=config_content,
    )


def render_start_master_script(
    deploy_path: str,
    pkg_name: str,
    config_file: str,
    dts_node_name: str,
    listen_port: int | None = None,
) -> str:
    return _render(
        start_mysql_dts_master_template,
        deploy_path=deploy_path,
        pkg_name=pkg_name,
        config_file=config_file,
        dts_node_name=dts_node_name,
        listen_port=listen_port if listen_port is not None else MYSQL_DTS_MASTER_PORT,
    )


def render_start_worker_script(
    deploy_path: str,
    pkg_name: str,
    config_file: str,
    dts_node_name: str,
    listen_port: int | None = None,
) -> str:
    return _render(
        start_mysql_dts_worker_template,
        deploy_path=deploy_path,
        pkg_name=pkg_name,
        config_file=config_file,
        dts_node_name=dts_node_name,
        listen_port=listen_port if listen_port is not None else MYSQL_DTS_WORKER_PORT,
    )


def render_stop_process_script(deploy_path: str) -> str:
    return _render(stop_mysql_dts_process_template, deploy_path=deploy_path)


def render_clean_data_dir_script(deploy_path: str) -> str:
    return _render(clean_mysql_dts_data_dir_template, deploy_path=deploy_path)


def _append_rm_rf_if_exists(lines: list[str], path: str) -> None:
    """路径不存在则跳过（幂等）；存在则 ``rm -rf``，权限错误仍失败。"""
    quoted = shlex.quote(path)
    lines.append(f"if [[ -e {quoted} || -L {quoted} ]]; then")
    lines.append(f"  rm -rf -- {quoted}")
    lines.append("fi")


def render_clean_ticket_dump_script(dump_dirs: list[str]) -> str:
    """删除本单 builtin dump 目录（缺目录视为成功）。不删 myloader 备份目录。"""
    lines = ["set -euo pipefail"]
    for path in dump_dirs:
        if not path:
            continue
        _append_rm_rf_if_exists(lines, path)
    lines.append("echo cleaned ticket dump dirs")
    return "\n".join(lines) + "\n"


def render_clean_cluster_relay_and_dump_script(
    deploy_path: str,
    worker_node_names: list[str],
    extra_exported_data_dirs: list[str] | None = None,
) -> str:
    """下架时显式删除各 worker ``{node}-data`` 与整棵 ``exported_data``。缺目录不失败。"""
    lines = ["set -euo pipefail"]
    deploy_path = (deploy_path or "").rstrip("/")
    seen = set()
    for node_name in worker_node_names:
        if not node_name:
            continue
        relay_dir = f"{deploy_path}/{node_name}-data"
        if relay_dir in seen:
            continue
        seen.add(relay_dir)
        _append_rm_rf_if_exists(lines, relay_dir)
    exported = f"{deploy_path}/exported_data"
    if exported not in seen:
        seen.add(exported)
        _append_rm_rf_if_exists(lines, exported)
    for extra in extra_exported_data_dirs or []:
        extra_path = (extra or "").rstrip("/")
        if not extra_path or extra_path in seen:
            continue
        seen.add(extra_path)
        _append_rm_rf_if_exists(lines, extra_path)
    lines.append("echo cleaned dts relay and exported_data")
    return "\n".join(lines) + "\n"


# 重装共用：解压到 packages 隔离目录后，将 deploy_path/bin 整目录软链到新包 bin（不动 conf）
_REINSTALL_EXTRACT_AND_LINK_BIN = """
# 解压到隔离目录：{deploy_path}/packages/{pkg_basename}/
PKG_BASENAME="${PKG_NAME%.tar*}"
PKG_ROOT="${DEPLOY_PATH}/packages/${PKG_BASENAME}"
mkdir -p "${PKG_ROOT}"
if ! tar -zxf "${PKG_FILE}" -C "${PKG_ROOT}" --strip-components=1 2>/dev/null; then
  tar -xf "${PKG_FILE}" -C "${PKG_ROOT}" --strip-components=1
fi
PKG_BIN="${PKG_ROOT}/bin"
if [[ ! -d "${PKG_BIN}" ]]; then
  echo "package bin missing after extract, expect ${PKG_BIN}" >&2
  ls -la "${PKG_ROOT}" || true
  exit 1
fi
chmod +x "${PKG_BIN}"/* 2>/dev/null || true

# 整目录软链：{deploy_path}/bin -> {pkg_root}/bin（不动 conf）
# 兼容：bin 已是软链（只删链接，绝不跟链清掉旧 packages）；bin 是普通目录（首次重装）则 rm -rf
# 注意：路径不要带尾部 /，避免 rm 跟随软链删目标内容
if [[ -L "${BIN_DIR}" ]]; then
  rm -f "${BIN_DIR}"
elif [[ -d "${BIN_DIR}" ]]; then
  rm -rf "${BIN_DIR}"
elif [[ -e "${BIN_DIR}" ]]; then
  rm -f "${BIN_DIR}"
fi
ln -sfn "${PKG_BIN}" "${BIN_DIR}"
"""

# 重装脚本模板：将新介质解压到隔离目录，整目录软链 bin，用原 conf 拉起
# 注意：绝不修改 conf/ 目录下的任何文件
reinstall_mysql_dts_master_template = (
    """
set -euo pipefail
DEPLOY_PATH="{{deploy_path}}"
PKG_NAME="{{pkg_name}}"
DTS_NODE_NAME="{{dts_node_name}}"
BIN_DIR="${DEPLOY_PATH}/bin"
CONF_DIR="${DEPLOY_PATH}/conf"
LOG_DIR="${DEPLOY_PATH}/log"
PKG_FILE="/data/install/${PKG_NAME}"
OUTPUT_FILE="${LOG_DIR}/${DTS_NODE_NAME}.output"

if [[ -z "${PKG_NAME}" ]]; then
  echo "pkg_name is empty" >&2
  exit 1
fi
if [[ -z "${DTS_NODE_NAME}" ]]; then
  echo "dts_node_name is empty" >&2
  exit 1
fi
if [[ ! -f "${PKG_FILE}" ]]; then
  echo "DTS package not found: ${PKG_FILE}" >&2
  ls -la /data/install/ || true
  exit 1
fi
if [[ ! -f "${CONF_DIR}/{{config_file}}" ]]; then
  echo "Config file not found: ${CONF_DIR}/{{config_file}}" >&2
  ls -la "${CONF_DIR}/" || true
  exit 1
fi
"""
    + _REINSTALL_EXTRACT_AND_LINK_BIN
    + """
if [[ ! -x "${BIN_DIR}/dm-master" ]]; then
  echo "dm-master missing after bin link, expect ${BIN_DIR}/dm-master" >&2
  ls -la "${BIN_DIR}" || true
  exit 1
fi
mkdir -p "${LOG_DIR}"
"""
    + _START_DAEMON_HELPER
    + """
start_daemon "${BIN_DIR}/dm-master" "${CONF_DIR}/{{config_file}}" "${OUTPUT_FILE}"

LISTEN_PORT="{{listen_port}}"
is_port_listen() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])${port}$"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])${port}$"
  else
    (echo >"/dev/tcp/127.0.0.1/${port}") >/dev/null 2>&1
  fi
}

ready=0
for _i in $(seq 1 10); do
  if pgrep -f "${BIN_DIR}/dm-master" >/dev/null 2>&1 && is_port_listen "${LISTEN_PORT}"; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "${ready}" -ne 1 ]]; then
  echo "dm-master failed to become ready (process/port ${LISTEN_PORT}):" >&2
  cat "${OUTPUT_FILE}" >&2 || true
  exit 1
fi
echo "reinstalled dm-master ${DTS_NODE_NAME} (listen ${LISTEN_PORT})"
"""
)

reinstall_mysql_dts_worker_template = (
    """
set -euo pipefail
DEPLOY_PATH="{{deploy_path}}"
PKG_NAME="{{pkg_name}}"
DTS_NODE_NAME="{{dts_node_name}}"
BIN_DIR="${DEPLOY_PATH}/bin"
CONF_DIR="${DEPLOY_PATH}/conf"
LOG_DIR="${DEPLOY_PATH}/log"
PKG_FILE="/data/install/${PKG_NAME}"
OUTPUT_FILE="${LOG_DIR}/${DTS_NODE_NAME}.output"

if [[ -z "${PKG_NAME}" ]]; then
  echo "pkg_name is empty" >&2
  exit 1
fi
if [[ -z "${DTS_NODE_NAME}" ]]; then
  echo "dts_node_name is empty" >&2
  exit 1
fi
if [[ ! -f "${PKG_FILE}" ]]; then
  echo "DTS package not found: ${PKG_FILE}" >&2
  ls -la /data/install/ || true
  exit 1
fi
if [[ ! -f "${CONF_DIR}/{{config_file}}" ]]; then
  echo "Config file not found: ${CONF_DIR}/{{config_file}}" >&2
  ls -la "${CONF_DIR}/" || true
  exit 1
fi
"""
    + _REINSTALL_EXTRACT_AND_LINK_BIN
    + """
if [[ ! -x "${BIN_DIR}/dm-worker" ]]; then
  echo "dm-worker missing after bin link, expect ${BIN_DIR}/dm-worker" >&2
  ls -la "${BIN_DIR}" || true
  exit 1
fi
mkdir -p "${LOG_DIR}"
"""
    + _START_DAEMON_HELPER
    + """
start_daemon "${BIN_DIR}/dm-worker" "${CONF_DIR}/{{config_file}}" "${OUTPUT_FILE}"

LISTEN_PORT="{{listen_port}}"
is_port_listen() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])${port}$"
  elif command -v netstat >/dev/null 2>&1; then
    netstat -ltn 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])${port}$"
  else
    (echo >"/dev/tcp/127.0.0.1/${port}") >/dev/null 2>&1
  fi
}

ready=0
for _i in $(seq 1 10); do
  if pgrep -f "${BIN_DIR}/dm-worker" >/dev/null 2>&1 && is_port_listen "${LISTEN_PORT}"; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "${ready}" -ne 1 ]]; then
  echo "dm-worker failed to become ready (process/port ${LISTEN_PORT}):" >&2
  cat "${OUTPUT_FILE}" >&2 || true
  exit 1
fi
echo "reinstalled dm-worker ${DTS_NODE_NAME} (listen ${LISTEN_PORT})"
"""
)


def render_reinstall_master_script(
    deploy_path: str,
    pkg_name: str,
    config_file: str,
    dts_node_name: str,
    listen_port: int | None = None,
) -> str:
    """渲染重装 Master 脚本：解压到隔离目录 + 整目录软链 bin + 用原 conf 拉起。"""
    return _render(
        reinstall_mysql_dts_master_template,
        deploy_path=deploy_path,
        pkg_name=pkg_name,
        config_file=config_file,
        dts_node_name=dts_node_name,
        listen_port=listen_port if listen_port is not None else MYSQL_DTS_MASTER_PORT,
    )


def render_reinstall_worker_script(
    deploy_path: str,
    pkg_name: str,
    config_file: str,
    dts_node_name: str,
    listen_port: int | None = None,
) -> str:
    """渲染重装 Worker 脚本：解压到隔离目录 + 整目录软链 bin + 用原 conf 拉起。"""
    return _render(
        reinstall_mysql_dts_worker_template,
        deploy_path=deploy_path,
        pkg_name=pkg_name,
        config_file=config_file,
        dts_node_name=dts_node_name,
        listen_port=listen_port if listen_port is not None else MYSQL_DTS_WORKER_PORT,
    )
