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
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend import env
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.exec_shell_script import ExecuteShellScriptComponent

ActConfig = Tuple[str, str, Dict[str, object], str]
_SCRIPT_CACHE: str = ""
_HEREDOC_DELIMITER = "CLEAN_RESIDUAL_EXPORTER_SCRIPT"


@dataclass(frozen=True)
class DBShellConfig:
    exporters: List[str]
    dry_run: bool
    enable_reload: bool
    clean_act_name: str
    sub_name: str


UNIFIED_DB_SHELL_CONFIG = DBShellConfig(
    exporters=[],
    dry_run=False,
    enable_reload=True,
    clean_act_name=_("清理 exporter 残留"),
    sub_name=_("exporter残留清理"),
)


def _load_clean_script_content() -> str:
    global _SCRIPT_CACHE
    if _SCRIPT_CACHE:
        return _SCRIPT_CACHE
    script_path = Path(__file__).resolve().with_name("clean_residual_exporter_exec.py")
    if not script_path.exists():
        raise FileNotFoundError("clean residual exporter script not found: {}".format(script_path))
    _SCRIPT_CACHE = script_path.read_text(encoding="utf-8")
    if _HEREDOC_DELIMITER in _SCRIPT_CACHE.splitlines():
        raise ValueError(f"script content contains heredoc delimiter line: {_HEREDOC_DELIMITER}")
    return _SCRIPT_CACHE


def _format_bool(value: bool) -> str:
    return "true" if value else "false"


def _build_shell_command(config: DBShellConfig, base_dir: str) -> str:
    script_content = _load_clean_script_content()
    exporters = ",".join(config.exporters)
    exporters_arg = ""
    if exporters:
        exporters_arg = " --exporters {exporters}".format(exporters=shlex.quote(exporters))
    return (
        'PYBIN=""; '
        'if command -v python3 >/dev/null 2>&1; then PYBIN="python3"; '
        'elif command -v python >/dev/null 2>&1; then PYBIN="python"; '
        'else echo "level=error msg=python_not_found detail=python3_or_python_required" >&2; exit 1; fi; '
        '"${{PYBIN}}" - --base-dir {base_dir}{exporters_arg} '
        "--dry-run {dry_run} --enable-reload {enable_reload} <<'{delimiter}'\n"
        "{script}\n"
        "{delimiter}"
    ).format(
        base_dir=shlex.quote(base_dir),
        exporters_arg=exporters_arg,
        dry_run=_format_bool(config.dry_run),
        enable_reload=_format_bool(config.enable_reload),
        script=script_content.rstrip(),
        delimiter=_HEREDOC_DELIMITER,
    )


def _build_sub_process(p: Builder, clean_act_name: str, clean_kwargs: Dict[str, object], sub_name: str) -> SubProcess:
    sub_p = SubBuilder(root_id=p.root_id, data=p.data)
    sub_p.add_act(act_name=clean_act_name, act_component_code=ExecuteShellScriptComponent.code, kwargs=clean_kwargs)
    return sub_p.build_sub_process(sub_name=sub_name)


def _add_sub_pipeline(p: Builder, clean_act_name: str, clean_kwargs: Dict[str, object], sub_name: str) -> None:
    p.add_sub_pipeline(_build_sub_process(p, clean_act_name, clean_kwargs, sub_name))


def gse_agent_base_dir_from_beat_path() -> str:
    """
    Parse GSE agent base dir from MYSQL_CROND_BEAT_PATH.
    """
    beat_path = env.MYSQL_CROND_BEAT_PATH
    if not str(beat_path).strip():
        raise ValueError("MYSQL_CROND_BEAT_PATH is required and must not be empty")
    try:
        beat_path_obj = Path(str(beat_path).strip())
        if beat_path_obj.is_absolute() and len(beat_path_obj.parents) >= 3:
            return str(beat_path_obj.parents[2])
    except (OSError, ValueError, TypeError):
        pass
    raise ValueError(f"Failed to parse GSE Agent base dir from beat path: {beat_path}")


def _build_act_config(bk_cloud_id: int, iplist: List[str], base_dir: str, config: DBShellConfig) -> ActConfig:
    clean_kwargs: Dict[str, object] = {
        "bk_cloud_id": bk_cloud_id,
        "exec_ip": list(iplist),
        "print_ip_log_on_success": True,
        "cluster": {
            "shell_command": _build_shell_command(config=config, base_dir=base_dir),
        },
    }
    return (
        config.clean_act_name,
        clean_kwargs,
        config.sub_name,
    )


def build_clean_residual_exporter_sub_process(p: Builder, bk_cloud_id: int, iplist: List[str]) -> Optional[SubProcess]:
    """
    构建 exporter 残留清理子流程并返回 SubProcess，不挂载到主流程。
    调用方可自由决定串行 (add_sub_pipeline) 或并行 (add_parallel_sub_pipeline) 编排。
    iplist 为空时返回 None。
    """
    if not iplist:
        return None

    base_dir = gse_agent_base_dir_from_beat_path()
    clean_act_name, clean_kwargs, sub_name = _build_act_config(
        bk_cloud_id=bk_cloud_id, iplist=iplist, base_dir=base_dir, config=UNIFIED_DB_SHELL_CONFIG
    )
    return _build_sub_process(
        p=p,
        clean_act_name=clean_act_name,
        clean_kwargs=clean_kwargs,
        sub_name=sub_name,
    )


def add_clean_residual_exporter_acts(
    p: Builder, db_type: str, bk_cloud_id: int, bk_biz_id: int, iplist: List[str]
) -> None:
    """
    Add clean residual exporter acts by db type.

    保留 db_type / bk_biz_id 参数维持向后兼容；当前清理行为对所有 db 类型一致。
    """
    sub = build_clean_residual_exporter_sub_process(p=p, bk_cloud_id=bk_cloud_id, iplist=iplist)
    if sub is not None:
        p.add_sub_pipeline(sub)
