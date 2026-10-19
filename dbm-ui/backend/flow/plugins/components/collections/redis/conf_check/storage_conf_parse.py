# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Decode, parse and compare ``storage_conf`` host blocks emitted by
``build_storage_conf_check_snippet``.

Kept free of Django imports so it can be unit-tested in isolation. Directive parsing and
value normalization mirror dbactuator ``pkg/redisconf`` (``ParseDirectives``,
``EffectiveReplicationOf``, ``sameConfRuntimeValue``, ``SamePathValue``); rule changes
there must be mirrored here.
"""
import base64
import binascii
import gzip
import os
import re
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

CONFCHK_ERR_PREFIX = "#CONFCHK_ERR"
REPLICATION_DIRECTIVES = ("replicaof", "slaveof")
SECTIONS = ("disk", "repl", "mem")

_STORE_MASTER_KEY = re.compile(r"^rocksdb(\d+)_master$")


@dataclass
class DiskConf:
    # directive (lowercased) -> every value in file order
    directives: Dict[str, List[str]] = field(default_factory=dict)
    # "<reason> <path>" from #CONFCHK_ERR lines written during include expansion
    include_errors: List[str] = field(default_factory=list)
    # last effective slaveof/replicaof value ("" when absent or "no one")
    replication_of: str = ""
    # basenames of loadmodule .so files
    modules: List[str] = field(default_factory=list)

    def last_value(self, name: str) -> Optional[str]:
        values = self.directives.get(name)
        return values[-1] if values else None


@dataclass
class StoreMaster:
    store_id: int
    ip: str
    port: str
    state: str

    @property
    def address(self) -> str:
        return "{}:{}".format(self.ip, self.port)


@dataclass
class StorageHostData:
    conf_path: str = ""
    conf_paths: List[str] = field(default_factory=list)
    disk: Optional[DiskConf] = None
    repl: Optional[Dict[str, str]] = None
    store_masters: List[StoreMaster] = field(default_factory=list)
    mem: Optional[Dict[str, str]] = None
    mem_cmd: str = ""
    # section ("disk" / "repl" / "mem") -> fixed reason token
    section_errors: Dict[str, str] = field(default_factory=dict)
    # whole-host failure from the job pipeline (job_failed, no_confchk_output, ...)
    collection_error: str = ""


def decode_section(value: str) -> str:
    """base64 + gunzip one payload section. Raises ValueError when undecodable."""
    try:
        return gzip.decompress(base64.b64decode(value, validate=True)).decode("utf-8", errors="replace")
    except (binascii.Error, OSError, EOFError, zlib.error) as e:
        raise ValueError("decode_failed: {}".format(e))


def _split_directive(line: str) -> Tuple[str, str]:
    parts = line.split(None, 1)
    name = parts[0].lower()
    value = parts[1].strip() if len(parts) > 1 else ""
    return name, value


def parse_disk_conf(text: str) -> DiskConf:
    conf = DiskConf()
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if line.startswith(CONFCHK_ERR_PREFIX):
            conf.include_errors.append(line[len(CONFCHK_ERR_PREFIX) :].strip())
            continue
        if not line or line.startswith("#"):
            continue
        name, value = _split_directive(line)
        conf.directives.setdefault(name, []).append(value)
        if name in REPLICATION_DIRECTIVES:
            # "slaveof no one" cancels replication but still overrides earlier values
            conf.replication_of = "" if (not value or value.lower() == "no one") else value
    for value in conf.directives.get("loadmodule", []):
        so_path = value.split()[0] if value.split() else ""
        if so_path:
            conf.modules.append(os.path.basename(so_path.strip("\"'")))
    return conf


def parse_info(text: str) -> Dict[str, str]:
    info: Dict[str, str] = {}
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        info[key.strip()] = value.strip()
    return info


def parse_store_masters(info: Dict[str, str]) -> List[StoreMaster]:
    """Tendisplus per-store replication sources: rocksdb<N>_master:ip=..,port=..,state=.."""
    stores = []
    for key, value in info.items():
        match = _STORE_MASTER_KEY.match(key)
        if not match:
            continue
        attrs = dict(item.split("=", 1) for item in value.split(",") if "=" in item)
        stores.append(
            StoreMaster(
                store_id=int(match.group(1)),
                ip=attrs.get("ip", ""),
                port=attrs.get("port", ""),
                state=attrs.get("state", ""),
            )
        )
    return sorted(stores, key=lambda s: s.store_id)


def parse_config_pairs(text: str) -> Optional[Dict[str, str]]:
    """Pair raw CONFIG GET * lines (key, value, key, value, ...). None when the count is odd."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    lines = [line[:-1] if line.endswith("\r") else line for line in lines]
    if len(lines) % 2:
        return None
    return {lines[i].strip().lower(): lines[i + 1] for i in range(0, len(lines), 2)}


def parse_storage_host_block(block: Optional[Dict]) -> StorageHostData:
    """Turn a parsed <CONFCHK checker="storage_conf"> JSON body into structured data."""
    data = StorageHostData()
    if not block:
        data.collection_error = "no_host_data"
        return data
    if block.get("error"):
        data.collection_error = str(block["error"])
        return data

    data.conf_path = block.get("conf_path") or ""
    data.conf_paths = list(block.get("conf_paths") or [])
    data.mem_cmd = block.get("mem_cmd") or ""

    texts: Dict[str, str] = {}
    for section in SECTIONS:
        err = block.get("{}_err".format(section)) or ""
        if err:
            data.section_errors[section] = err
            continue
        encoded = block.get(section) or ""
        if not encoded:
            data.section_errors[section] = "missing_section"
            continue
        try:
            texts[section] = decode_section(encoded)
        except ValueError:
            data.section_errors[section] = "decode_failed"

    if "disk" in texts:
        data.disk = parse_disk_conf(texts["disk"])
    if "repl" in texts:
        info = parse_info(texts["repl"])
        if "role" not in info:
            data.section_errors["repl"] = "repl_unparsable"
        else:
            data.repl = info
            data.store_masters = parse_store_masters(info)
    if "mem" in texts:
        pairs = parse_config_pairs(texts["mem"])
        if pairs is None:
            data.section_errors["mem"] = "mem_unpaired"
        else:
            data.mem = pairs
    return data


# ---------------------------------------------------------------------------
# dbconfig baseline vs memory vs disk
# ---------------------------------------------------------------------------

# Credentials, special-cased checks (replication, modules) and process-management directives.
EXCLUDED_DIRECTIVES = frozenset(
    {
        "requirepass",
        "masterauth",
        "masteruser",
        "user",
        "rename-command",
        "loadmodule",
        "slaveof",
        "replicaof",
        "cluster-config-file",
        "daemonize",
        "supervised",
    }
)
# Overwritten at deploy/run time (dbmon, host hardware) so static dbconfig defaults don't apply.
DYNAMIC_DIRECTIVES = frozenset(
    {
        "maxmemory",
        "appendonly",
        "rocks.blockcachemb",
        "rocks.write_buffer_size",
        "netiothreadnum",
        "executorthreadnum",
        "executorworkpoolsize",
        "rocks.max_background_jobs",
        "rocks.max_background_compactions",
        "migratesenderthreadnum",
        "migratereceivethreadnum",
        "migrateclearthreadnum",
    }
)
# Directives written as several lines on disk but stored as one dbconfig item
# (value embeds "\n<name> " between entries).
MULTI_ENTRY_DIRECTIVES = frozenset({"save", "client-output-buffer-limit"})
PATH_DIRECTIVES = frozenset({"dir", "pidfile", "logfile", "unixsocket", "dumpdir", "logdir", "slowlog"})

# legacy name -> current name; same as dbactuator confNameAliasPairs
CONF_NAME_ALIASES = {
    "slave-priority": "replica-priority",
    "slave-read-only": "replica-read-only",
    "slave-serve-stale-data": "replica-serve-stale-data",
    "slave-lazy-flush": "replica-lazy-flush",
    "slave-announce-ip": "replica-announce-ip",
    "slave-announce-port": "replica-announce-port",
    "min-slaves-to-write": "min-replicas-to-write",
    "min-slaves-max-lag": "min-replicas-max-lag",
    "cluster-slave-no-failover": "cluster-replica-no-failover",
    "cluster-slave-validity-factor": "cluster-replica-validity-factor",
    "hash-max-ziplist-entries": "hash-max-listpack-entries",
    "hash-max-ziplist-value": "hash-max-listpack-value",
    "zset-max-ziplist-entries": "zset-max-listpack-entries",
    "zset-max-ziplist-value": "zset-max-listpack-value",
    "list-max-ziplist-size": "list-max-listpack-size",
    "slowlog-log-slower-than": "commandlog-execution-slower-than",
    "slowlog-max-len": "commandlog-slow-execution-max-len",
}
_ALIAS_INDEX = {**CONF_NAME_ALIASES, **{v: k for k, v in CONF_NAME_ALIASES.items()}}

_TRUTHY = frozenset({"yes", "true", "on", "1"})
_FALSY = frozenset({"no", "false", "off", "0"})
_MEM_UNITS = (
    ("tb", 1024**4),
    ("gb", 1024**3),
    ("mb", 1024**2),
    ("kb", 1024),
    ("t", 1024**4),
    ("g", 1024**3),
    ("m", 1024**2),
    ("k", 1024),
    ("b", 1),
)
_PLACEHOLDER = re.compile(r"\{\{[^}]*\}\}")

ABSENT = "<absent>"


@dataclass
class DirectiveDrift:
    name: str
    expected: str
    memory: Optional[str]  # None when memory was not compared
    disk: Optional[str]  # None when disk was not compared

    def render(self) -> str:
        parts = ["dbconfig={}".format(self.expected)]
        if self.memory is not None:
            parts.append("memory={}".format(self.memory))
        if self.disk is not None:
            parts.append("disk={}".format(self.disk))
        return "{}({})".format(self.name, ", ".join(parts))


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _bool_equal(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    return (a in _TRUTHY and b in _TRUTHY) or (a in _FALSY and b in _FALSY)


def _has_mem_unit(s: str) -> bool:
    s = s.strip().lower()
    for suffix, _mul in _MEM_UNITS:
        if s.endswith(suffix) and len(s) > len(suffix):
            try:
                float(s[: -len(suffix)])
                return True
            except ValueError:
                continue
    return False


def parse_mem_bytes(s: str) -> Optional[int]:
    """redis memory units: 1kb = 1024, 1mb = 1024^2; a bare number is bytes."""
    s = s.strip().lower()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    for suffix, mul in _MEM_UNITS:
        if s.endswith(suffix):
            try:
                return int(float(s[: -len(suffix)].strip()) * mul)
            except ValueError:
                return None
    return None


def _same_token(a: str, b: str) -> bool:
    if a.lower() == b.lower() or _bool_equal(a, b):
        return True
    if _has_mem_unit(a) or _has_mem_unit(b):
        ba, bb = parse_mem_bytes(a), parse_mem_bytes(b)
        return ba is not None and bb is not None and ba == bb
    return False


def same_conf_value(a: str, b: str) -> bool:
    """Tolerates quotes, case, yes/no vs 1/0 and redis memory units (256mb == 268435456)."""
    a, b = unquote(a), unquote(b)
    if a == b or (a in ("", '""') and b in ("", '""')):
        return True
    if _bool_equal(a, b):
        return True
    ta, tb = a.split(), b.split()
    return len(ta) == len(tb) and all(_same_token(x, y) for x, y in zip(ta, tb))


def _normalize_path(value: str) -> str:
    path = os.path.normpath(unquote(value)) if unquote(value) else ""
    if path == "/data1" or path.startswith("/data1/"):
        path = "/data" + path[len("/data1") :]
    return path


def same_conf_value_for(name: str, a: str, b: str) -> bool:
    if same_conf_value(a, b):
        return True
    if name in PATH_DIRECTIVES:
        return bool(unquote(a)) and _normalize_path(a) == _normalize_path(b)
    return False


def join_directive_values(values: List[str]) -> str:
    return " ".join(unquote(v) for v in values)


def split_dbconfig_entries(name: str, value: str) -> List[str]:
    """'normal 256mb 512mb 300\\nclient-output-buffer-limit slave ...' -> one entry per line."""
    entries = []
    for index, line in enumerate(value.split("\n")):
        line = line.strip()
        if index > 0:
            head, _sep, rest = line.partition(" ")
            if head.lower() == name:
                line = rest.strip()
        if line or index == 0:
            entries.append(line)
    return entries


def resolve_expected_conf(
    dbconfig: Dict[str, str],
    *,
    ip: str,
    port: int,
    cluster_enabled: bool,
    check_databases: bool,
) -> Dict[str, List[str]]:
    """
    Turn a cluster dbconfig map into expected directive entries for one instance.

    Placeholders that are instance facts are substituted; directives that are excluded,
    dynamically overwritten, or still hold an unresolved placeholder are dropped.
    """
    replacements = (
        ("{{port}}", str(port)),
        ("{{address}}", ip),
        ("{{redis_data_dir}}", "/data/redis/{}".format(port)),
        ("{{cluster_enabled}}", "yes" if cluster_enabled else "no"),
    )
    expected: Dict[str, List[str]] = {}
    for raw_name, raw_value in (dbconfig or {}).items():
        name = str(raw_name).strip().lower()
        if not name or name in EXCLUDED_DIRECTIVES or name in DYNAMIC_DIRECTIVES:
            continue
        if name == "databases" and not check_databases:
            continue
        value = "" if raw_value is None else str(raw_value)
        for placeholder, replacement in replacements:
            value = value.replace(placeholder, replacement)
        if _PLACEHOLDER.search(value):
            continue
        expected[name] = split_dbconfig_entries(name, value.strip())
    return expected


def _lookup_with_alias(mapping: Dict, name: str):
    if name in mapping:
        return mapping[name]
    alias = _ALIAS_INDEX.get(name)
    if alias and alias in mapping:
        return mapping[alias]
    return None


def _display(value: str, limit: int = 80) -> str:
    shown = unquote(value)
    if shown == "":
        shown = '""'
    return shown if len(shown) <= limit else shown[: limit - 3] + "..."


def compare_directives(
    expected: Dict[str, List[str]],
    disk: Optional[DiskConf],
    memory: Optional[Dict[str, str]],
) -> List[DirectiveDrift]:
    """
    Compare each expected directive with runtime memory and the on-disk config.

    Directives only on disk or in memory are ignored. A directive absent from both is
    skipped (not supported by this version, or not rendered); a directive CONFIG GET does
    not return is compared against disk only. ``disk``/``memory`` of None skip that side.
    """
    drifts = []
    for name in sorted(expected):
        entries = expected[name]
        want = join_directive_values(entries)

        mem_value = _lookup_with_alias(memory, name) if memory is not None else None
        disk_values = _lookup_with_alias(disk.directives, name) if disk is not None else None

        if mem_value is None and not disk_values:
            continue

        mem_shown = None
        if mem_value is not None and not same_conf_value_for(name, want, mem_value):
            mem_shown = _display(mem_value)

        disk_drift = False
        disk_display = None
        if disk is not None:
            if not disk_values:
                disk_display = ABSENT
                # rendering skips empty values except `save ""`
                disk_drift = want != "" or name == "save"
            else:
                have = join_directive_values(disk_values) if name in MULTI_ENTRY_DIRECTIVES else disk_values[-1]
                disk_display = _display(have)
                disk_drift = not same_conf_value_for(name, want, have)

        if mem_shown is None and not disk_drift:
            continue
        drifts.append(
            DirectiveDrift(
                name=name,
                expected=_display(want),
                memory=_display(mem_value) if mem_value is not None else None,
                disk=disk_display,
            )
        )
    return drifts
