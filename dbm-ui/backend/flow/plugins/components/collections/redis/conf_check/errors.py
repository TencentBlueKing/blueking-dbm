# -*- coding: utf-8 -*-
"""Shared conf-check collection error codes and classifiers."""

from typing import Dict, List, Tuple

HostConfKey = Tuple[str, str, int]


def format_password_drs_error(reason: str) -> str:
    return "password_unavailable: {}".format(reason)


def is_host_collection_error(err: str) -> bool:
    """True when host_block['error'] reflects Job/log pipeline failure, not conf read."""
    if not err or err in ("conf_not_found", "no_host_data"):
        return False
    return err in (
        "job_failed",
        "job_timeout",
        "empty_log",
        "no_confchk_output",
        "no_step_instance_id",
        "bad_json",
    ) or (err.startswith("log_fetch_") or err.startswith("job_issue_"))


def mark_host_targets(
    host_conf_data: Dict[HostConfKey, Dict], exec_ip: str, conf_targets: List[Dict], reason: str
) -> None:
    for ct in conf_targets:
        host_conf_data.setdefault((ct["checker"], exec_ip, ct["port"]), {"error": reason})
