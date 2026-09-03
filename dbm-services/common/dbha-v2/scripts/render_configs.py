#!/usr/bin/env python3
# MIT License — same as dbha-v2 module
"""Render dbha-v2 etc/*.yaml from templates and an rc key-value file."""

from typing import Dict, List, Match, Optional, Tuple

import argparse
import re
import socket
import struct
import sys
from pathlib import Path

try:
    import fcntl
except ImportError:
    # fcntl is Unix-only; on Windows the interface-ioctl fallback is unavailable,
    # so _get_iface_ipv4 degrades to returning None (the UDP-based primary path in
    # _guess_primary_ipv4 still works). This import guard does not affect Linux,
    # where fcntl imports normally and the ioctl fallback is preserved.
    fcntl = None

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
_KEY_LINE_RE = re.compile(r"^([A-Z0-9_]+)=(.*)$")

# APM listen defaults (server: admin/receiver/analysis).
_DEFAULT_ADMIN_APM_LISTEN_PORT = 50080
_DEFAULT_RECEIVER_APM_LISTEN_PORT = 50081
_DEFAULT_ANALYSIS_APM_LISTEN_PORT = 50082

# receiver -> probe endpoint default.
_DEFAULT_RECEIVER_SOURCE_PROBE_PORT = 50052

# admin network ports.
_DEFAULT_ADMIN_GRPC_LISTEN_PORT = 50051
_DEFAULT_ADMIN_WEB_LISTEN_PORT = 50060

# probe install directory default (must match deploy.sh -t target).
_DEFAULT_PROBE_INSTALL_DIR = "/usr/local/dbha-v2"

# probe reporter local socket port default; "0" means unset -> probe falls back to
# the GSE domain socket at runtime (used by Windows probes to report via local TCP).
_DEFAULT_PROBE_REPORTER_LOCAL_SOCKET_PORT = "0"
_DEFAULT_ADMIN_PROBE_GSE_LOCAL_SOCKET_PORT = "0"

# Periodic config sync defaults. "0s" leaves sync off, which is what a deployment upgraded from
# an rc predating these keys must keep doing: enabling it silently would start unattended
# rewrites of probe.yaml on every existing machine.
_DEFAULT_PROBE_ADMIN_SYNC_INTERVAL = "0s"
_DEFAULT_PROBE_ADMIN_BK_CLOUD_ID = "0"

# Admin metadata cache freshness defaults. Empty means the admin binary applies its own
# defaults (10m / 24h), so the rendered file does not pin values the code may revise.
_DEFAULT_ADMIN_PROBE_METADATA_CACHE_MAX_AGE = "10m"
_DEFAULT_ADMIN_PROBE_METADATA_TOMBSTONE_AGE = "24h"

# IP detection and fallback.
_IP_DETECT_UDP_CONNECT_PORT = 80
_DEFAULT_LOOPBACK_IPV4 = "127.0.0.1"
_FALLBACK_NET_IFACE = "eth1"

# rc parsing helpers.
_RC_SNIPPET_FILE_SUFFIX = "_YAML_FILE"

_MODULE_SERVER = "server"
_MODULE_PROBE = "probe"
_MODULE_TEMPLATES = {
    _MODULE_SERVER: ("admin.yaml", "analysis.yaml", "receiver.yaml"),
    _MODULE_PROBE: ("probe.yaml",),
}

_PROBE_INSTALL_DIR_ALLOWED_RE = re.compile(r"^[A-Za-z0-9_./~-]+$")


def validate_probe_install_dir(install_dir: str) -> None:
    """Validate probe install directory; rules align with Go validateProbeWorkdir."""
    if ".." in install_dir:
        raise ValueError("path traversal")

    if not (
        install_dir.startswith("/")
        or install_dir.startswith("~")
        or install_dir.startswith(".")
    ):
        raise ValueError("invalid prefix")

    if not _PROBE_INSTALL_DIR_ALLOWED_RE.match(install_dir):
        raise ValueError("invalid character")


def parse_rc(content: str) -> Dict[str, str]:
    """Parse one KEY=value per line; quoted values must fit on a single line."""
    result: Dict[str, str] = {}

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _KEY_LINE_RE.match(stripped)
        if not m:
            continue

        key, rest = m.group(1), m.group(2).strip()
        if rest.startswith('"'):
            result[key] = _parse_double_quoted_line(rest)
        else:
            result[key] = _unescape_rc_value(rest)
    return result


def load_rc(path: Path) -> Dict[str, str]:
    return parse_rc(path.read_text(encoding="utf-8"))


def apply_admin_apm_listen_address_default(values: Dict[str, str], ip_detect_host: str) -> None:
    """If ADMIN_APM_LISTEN_ADDRESS is unset or empty, set http://<primary IPv4>:50080."""
    _apply_apm_listen_address_default(
        values, ip_detect_host,
        key="ADMIN_APM_LISTEN_ADDRESS",
        port=_DEFAULT_ADMIN_APM_LISTEN_PORT,
    )


def apply_receiver_apm_listen_address_default(values: Dict[str, str], ip_detect_host: str) -> None:
    """If RECEIVER_APM_LISTEN_ADDRESS is unset or empty, set http://<primary IPv4>:50081."""
    _apply_apm_listen_address_default(
        values, ip_detect_host,
        key="RECEIVER_APM_LISTEN_ADDRESS",
        port=_DEFAULT_RECEIVER_APM_LISTEN_PORT,
    )


def apply_analysis_apm_listen_address_default(values: Dict[str, str], ip_detect_host: str) -> None:
    """If ANALYSIS_APM_LISTEN_ADDRESS is unset or empty, set http://<primary IPv4>:50082."""
    _apply_apm_listen_address_default(
        values, ip_detect_host,
        key="ANALYSIS_APM_LISTEN_ADDRESS",
        port=_DEFAULT_ANALYSIS_APM_LISTEN_PORT,
    )


def apply_detector_check_probe_process_cmd_default(values: Dict[str, str]) -> None:
    """Fill PROBE_INSTALL_DIR and ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD when unset."""
    install_dir = values.get("PROBE_INSTALL_DIR", "").strip() or _DEFAULT_PROBE_INSTALL_DIR
    try:
        validate_probe_install_dir(install_dir)
    except ValueError as exc:
        sys.stderr.write("invalid PROBE_INSTALL_DIR, errmsg: {}\n".format(exc))
        sys.exit(1)

    if not values.get("PROBE_INSTALL_DIR", "").strip():
        values["PROBE_INSTALL_DIR"] = install_dir
    if not values.get("ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD", "").strip():
        values["ANALYSIS_DETECTOR_CHECK_PROBE_PROCESS_CMD"] = (
            "cd {} && ./bin/dbha-probe health -j".format(install_dir)
        )


def apply_probe_reporter_local_socket_port_default(values: Dict[str, str]) -> None:
    """Inject a default of "0" for PROBE_REPORTER_LOCAL_SOCKET_PORT when the rc omits it.

    probe.yaml is a shared Linux/Windows template that now references this
    placeholder. Existing Linux rc files predate the key; without a default the
    placeholder would stay unrendered and render_configs.py would treat it as an
    undefined placeholder and exit 1, breaking upgrades of existing deployments.
    Injecting "0" (meaning unset -> runtime falls back to the domain socket) keeps
    Linux behavior unchanged while allowing Windows rc files to set a real port.
    """
    if not values.get("PROBE_REPORTER_LOCAL_SOCKET_PORT", "").strip():
        values["PROBE_REPORTER_LOCAL_SOCKET_PORT"] = _DEFAULT_PROBE_REPORTER_LOCAL_SOCKET_PORT


def apply_admin_probe_gse_local_socket_port_default(values: Dict[str, str]) -> None:
    """Inject a default of "0" for ADMIN_PROBE_GSE_LOCAL_SOCKET_PORT when the rc omits it.

    admin.yaml now references this placeholder for probe GSE defaults returned via
    GetProbeConfig. Existing server rc files predate the key; without a default the
    placeholder would stay unrendered and break upgrades of existing deployments.
    """
    if not values.get("ADMIN_PROBE_GSE_LOCAL_SOCKET_PORT", "").strip():
        values["ADMIN_PROBE_GSE_LOCAL_SOCKET_PORT"] = _DEFAULT_ADMIN_PROBE_GSE_LOCAL_SOCKET_PORT


def apply_admin_probe_metadata_defaults(values: Dict[str, str]) -> None:
    """Fill the probeMetadata placeholders when the rc omits them.

    admin.yaml now carries a probeMetadata block. Server rc files written before it exists
    would leave the placeholders unrendered, which render_configs.py rejects, so an upgrade
    would fail on every existing deployment.
    """
    if not values.get("ADMIN_PROBE_METADATA_CACHE_MAX_AGE", "").strip():
        values["ADMIN_PROBE_METADATA_CACHE_MAX_AGE"] = _DEFAULT_ADMIN_PROBE_METADATA_CACHE_MAX_AGE
    if not values.get("ADMIN_PROBE_METADATA_TOMBSTONE_AGE", "").strip():
        values["ADMIN_PROBE_METADATA_TOMBSTONE_AGE"] = _DEFAULT_ADMIN_PROBE_METADATA_TOMBSTONE_AGE


def apply_probe_admin_sync_defaults(values: Dict[str, str], ip_detect_host: str) -> None:
    """Fill the probe admin block placeholders when the rc omits them.

    The interval defaults to "0s", leaving periodic sync off: an existing deployment upgrading
    to this template must not silently start rewriting its probe.yaml. Endpoints default to
    empty for the same reason, since sync also requires at least one.
    """
    endpoints = values.get("PROBE_ADMIN_ENDPOINTS", "").strip()
    values["PROBE_ADMIN_ENDPOINTS"] = _format_yaml_endpoint_list(endpoints)

    if not values.get("PROBE_ADMIN_BK_CLOUD_ID", "").strip():
        values["PROBE_ADMIN_BK_CLOUD_ID"] = _DEFAULT_PROBE_ADMIN_BK_CLOUD_ID
    if not values.get("PROBE_ADMIN_SYNC_INTERVAL", "").strip():
        values["PROBE_ADMIN_SYNC_INTERVAL"] = _DEFAULT_PROBE_ADMIN_SYNC_INTERVAL
    if not values.get("PROBE_ADMIN_LOCAL_IP", "").strip():
        values["PROBE_ADMIN_LOCAL_IP"] = _guess_primary_ipv4(ip_detect_host)


def _format_yaml_endpoint_list(raw: str) -> str:
    """Turn a comma/space separated endpoint list into quoted YAML flow-sequence items."""
    items = [item for item in re.split(r"[,;\s]+", raw) if item]
    return ", ".join('"{}"'.format(item) for item in items)


def _apply_apm_listen_address_default(
    values: Dict[str, str], ip_detect_host: str, key: str, port: int,
) -> None:
    """Shared helper: fill http://<primary IPv4>:<port> when *key* is unset or empty.

    Also handles the ``:NNNN`` shorthand by prepending the detected IPv4 host.
    """
    raw = values.get(key, "").strip()
    if not raw:
        host = _guess_primary_ipv4(ip_detect_host)
        values[key] = "http://{}:{}".format(host, port)
        sys.stderr.write(
            "{} unset, using default listen, port: {}\n".format(key, port)
        )
        return

    # Support ":port" shorthand — auto-detect host (same as gRPC listen address).
    if raw.startswith(":") and raw[1:].isdigit():
        host = _guess_primary_ipv4(ip_detect_host)
        values[key] = "http://{}{}".format(host, raw)
        sys.stderr.write(
            "{} missing host, using detected address with port from rc\n".format(key)
        )


def apply_receiver_source_probe_endpoint_default(values: Dict[str, str], ip_detect_host: str) -> None:
    """If RECEIVER_SOURCE_PROBE_ENDPOINT is unset or empty, set host:port for probe source."""
    raw = values.get("RECEIVER_SOURCE_PROBE_ENDPOINT", "").strip()
    if raw:
        return
    host = _guess_primary_ipv4(ip_detect_host)
    values["RECEIVER_SOURCE_PROBE_ENDPOINT"] = "{}:{}".format(host, _DEFAULT_RECEIVER_SOURCE_PROBE_PORT)
    sys.stderr.write(
        "RECEIVER_SOURCE_PROBE_ENDPOINT unset, using default endpoint, port: {}\n".format(
            _DEFAULT_RECEIVER_SOURCE_PROBE_PORT
        )
    )


def apply_admin_grpc_listen_address_default(values: Dict[str, str], ip_detect_host: str) -> None:
    """Unset/empty, or ':port' only: fill host using same IPv4 detection as APM/probe defaults."""
    raw = values.get("ADMIN_GRPC_LISTEN_ADDRESS", "").strip()
    if not raw:
        host = _guess_primary_ipv4(ip_detect_host)
        values["ADMIN_GRPC_LISTEN_ADDRESS"] = "{}:{}".format(host, _DEFAULT_ADMIN_GRPC_LISTEN_PORT)
        sys.stderr.write(
            "ADMIN_GRPC_LISTEN_ADDRESS unset, using default listen, port: {}\n".format(
                _DEFAULT_ADMIN_GRPC_LISTEN_PORT
            )
        )
        return
    if raw.startswith(":") and raw[1:].isdigit():
        host = _guess_primary_ipv4(ip_detect_host)
        values["ADMIN_GRPC_LISTEN_ADDRESS"] = "{}{}".format(host, raw)
        sys.stderr.write(
            "ADMIN_GRPC_LISTEN_ADDRESS missing host, using detected address with port from rc\n"
        )


def apply_admin_web_listen_address_default(values: Dict[str, str], ip_detect_host: str) -> None:
    """If ADMIN_WEB_LISTEN_ADDRESS is unset or empty, set http://<primary IPv4>:50060."""
    _apply_apm_listen_address_default(
        values, ip_detect_host,
        key="ADMIN_WEB_LISTEN_ADDRESS",
        port=_DEFAULT_ADMIN_WEB_LISTEN_PORT,
    )


def apply_receiver_source_probe_block(values: Dict[str, str], rc_path: Path) -> None:
    """Load receiver service.source probe entry from shard YAML (path relative to rc)."""
    _apply_shard_block(
        values, rc_path,
        file_key="RECEIVER_SOURCE_PROBE_SHARD_FILE",
        block_key="RECEIVER_SOURCE_PROBE_BLOCK",
        default_rel="templates/snippets/receiver_source_probe.yaml",
        err_label="receiver probe source shard file",
    )


def apply_receiver_source_kafka_block(values: Dict[str, str], rc_path: Path) -> None:
    """Load receiver service.source kafka entry from shard YAML (path relative to rc)."""
    _apply_shard_block(
        values, rc_path,
        file_key="RECEIVER_SOURCE_KAFKA_SHARD_FILE",
        block_key="RECEIVER_SOURCE_KAFKA_BLOCK",
        default_rel="templates/snippets/receiver_source_kafka.yaml",
        err_label="receiver kafka source shard file",
        prefix="\n",
    )


def apply_receiver_sink_mysql_block(values: Dict[str, str], rc_path: Path) -> None:
    """Load receiver service.sink mysql entry from shard YAML (path relative to rc)."""
    _apply_shard_block(
        values, rc_path,
        file_key="RECEIVER_SINK_MYSQL_SHARD_FILE",
        block_key="RECEIVER_SINK_MYSQL_BLOCK",
        default_rel="templates/snippets/receiver_sink_mysql.yaml",
        err_label="receiver sink mysql shard file",
    )


def apply_probe_mysql_shard_block(values: Dict[str, str], rc_path: Path) -> None:
    """Load mysql harvester shard YAML and substitute placeholders (after *_YAML_FILE)."""
    _apply_shard_block(
        values, rc_path,
        file_key="PROBE_MYSQL_SHARD_FILE",
        block_key="PROBE_MYSQL_SHARD_BLOCK",
        default_rel="templates/snippets/probe_mysql_shard.yaml",
        err_label="mysql shard file",
    )


def apply_probe_redis_shard_block(values: Dict[str, str], rc_path: Path) -> None:
    """Load redis shard YAML and substitute placeholders."""
    if not _redis_shard_enabled(values):
        values["PROBE_REDIS_SHARD_BLOCK"] = ""
        return

    _apply_shard_block(
        values, rc_path,
        file_key="PROBE_REDIS_SHARD_FILE",
        block_key="PROBE_REDIS_SHARD_BLOCK",
        default_rel="templates/snippets/probe_redis_shard.yaml",
        err_label="redis shard file",
        prefix="\n",
    )


def apply_yaml_snippet_files(values: Dict[str, str], rc_path: Path) -> None:
    """Expand KEY ending in _YAML_FILE into KEY without _FILE, with file body."""
    for k in list(values.keys()):
        if not k.endswith(_RC_SNIPPET_FILE_SUFFIX):
            continue
        rel = values[k].strip()
        if not rel:
            del values[k]
            continue

        target_key = k[: -len("_FILE")]
        path = _resolve_rc_relative_path(rc_path, rel)
        if not path.is_file():
            sys.stderr.write(
                "snippet file not found for {}: {}\n".format(k, path)
            )
            sys.exit(1)

        text = path.read_text(encoding="utf-8").rstrip("\n")
        values[target_key] = text
        del values[k]


def render_template(template_text: str, values: Dict[str, str]) -> str:
    # Use regex one-pass substitution to avoid secondary expansion when a value
    # itself contains {{ANOTHER_KEY}} literals.
    return _PLACEHOLDER_RE.sub(lambda m: _placeholder_replace(m, values), template_text)


def find_missing_placeholders(text: str) -> List[str]:
    return sorted(set(_PLACEHOLDER_RE.findall(text)))


def try_parse_yaml(path: Path, text: str) -> None:
    try:
        import yaml  # type: ignore
    except ImportError:
        return

    try:
        yaml.safe_load(text)
    except yaml.YAMLError as exc:
        sys.stderr.write(
            "yaml validation failed for {}, errmsg: {}\n".format(path.name, exc)
        )
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render dbha-v2 YAML configs from templates using an rc file.",
    )
    parser.add_argument(
        "--rc",
        type=Path,
        default=Path("etc/dbha-v2.rc"),
        help="rc file path (default: etc/dbha-v2.rc)",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        default=Path("etc/templates"),
        help="directory with *.yaml templates (default: etc/templates)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("etc"),
        help="output directory for rendered YAML (default: etc)",
    )
    parser.add_argument(
        "--no-validate-yaml",
        action="store_true",
        help="skip PyYAML syntax check when PyYAML is installed",
    )
    parser.add_argument(
        "--ip-detect-udp-connect-host",
        required=True,
        metavar="HOST",
        help=(
            "host for the UDP connect trick when inferring primary outbound IPv4 "
            "(e.g. a reachable resolver or gateway)"
        ),
    )
    parser.add_argument(
        "--module",
        required=True,
        choices=(_MODULE_SERVER, _MODULE_PROBE),
        help=(
            "which module to render: 'server' renders admin/analysis/receiver, "
            "'probe' renders probe only"
        ),
    )
    args = parser.parse_args()

    if not args.rc.is_file():
        sys.stderr.write("rc file not found: {}\n".format(args.rc))
        sys.exit(1)

    if not args.template_dir.is_dir():
        sys.stderr.write("template-dir not found: {}\n".format(args.template_dir))
        sys.exit(1)

    values = load_rc(args.rc)
    ip_detect_host = args.ip_detect_udp_connect_host
    rc_resolved = args.rc.resolve()

    # Module-scoped default injection and shard expansion: only touch the keys
    # that the selected module's templates actually consume.
    if args.module == _MODULE_SERVER:
        apply_admin_apm_listen_address_default(values, ip_detect_host)
        apply_receiver_apm_listen_address_default(values, ip_detect_host)
        apply_analysis_apm_listen_address_default(values, ip_detect_host)
        apply_detector_check_probe_process_cmd_default(values)
        apply_receiver_source_probe_endpoint_default(values, ip_detect_host)
        apply_admin_grpc_listen_address_default(values, ip_detect_host)
        apply_admin_web_listen_address_default(values, ip_detect_host)
        apply_admin_probe_gse_local_socket_port_default(values)
        apply_admin_probe_metadata_defaults(values)
    else:
        apply_probe_reporter_local_socket_port_default(values)
        apply_probe_admin_sync_defaults(values, ip_detect_host)

    # Phase 1: expand _YAML_FILE keys into raw YAML text (no placeholder rendering).
    apply_yaml_snippet_files(values, rc_resolved)

    # Phase 2: render shard blocks — each block may reference keys populated in
    #          earlier phases or in the rc itself.  Only render blocks needed by
    #          the selected module to avoid forcing the other module's keys.
    if args.module == _MODULE_SERVER:
        apply_receiver_source_probe_block(values, rc_resolved)
        apply_receiver_source_kafka_block(values, rc_resolved)
        apply_receiver_sink_mysql_block(values, rc_resolved)
    else:
        apply_probe_mysql_shard_block(values, rc_resolved)
        apply_probe_redis_shard_block(values, rc_resolved)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    selected_names = _MODULE_TEMPLATES[args.module]
    templates = [args.template_dir / name for name in selected_names]
    missing_templates = [str(p) for p in templates if not p.is_file()]
    if missing_templates:
        sys.stderr.write(
            "missing template files for module {}: {}\n".format(
                args.module, ", ".join(missing_templates)
            )
        )
        sys.exit(1)

    missing_report: List[str] = []
    rendered_results: List[Tuple[Path, str]] = []
    for tpl in templates:
        text = tpl.read_text(encoding="utf-8")
        rendered = render_template(text, values)
        for token in find_missing_placeholders(rendered):
            missing_report.append("{}: {}".format(tpl.name, token))
        rendered_results.append((args.out_dir / tpl.name, rendered))

    if missing_report:
        sys.stderr.write("undefined placeholders:\n")
        for line in missing_report:
            sys.stderr.write("  {}\n".format(line))
        sys.exit(1)

    for out_path, rendered in rendered_results:
        out_path.write_text(rendered, encoding="utf-8")
        if not args.no_validate_yaml:
            try_parse_yaml(out_path, rendered)

def _guess_primary_ipv4(ip_detect_host: str) -> str:
    """Best-effort primary IPv4 (outbound route); fallback loopback."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((ip_detect_host, _IP_DETECT_UDP_CONNECT_PORT))
            addr, _ = sock.getsockname()
            return addr
        finally:
            sock.close()
    except OSError:
        iface_addr = _get_iface_ipv4(_FALLBACK_NET_IFACE)
        return iface_addr if iface_addr else _DEFAULT_LOOPBACK_IPV4


def _get_iface_ipv4(ifname: str) -> Optional[str]:
    """Return IPv4 for interface *ifname* (Linux ioctl); None if unavailable."""
    if fcntl is None:
        return None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            ifreq = struct.pack("256s", ifname.encode("utf-8")[:15])
            res = fcntl.ioctl(sock.fileno(), 0x8915, ifreq)  # SIOCGIFADDR
            return socket.inet_ntoa(res[20:24])
        finally:
            sock.close()
    except OSError:
        return None


def _unescape(raw: str, stop_at_quote: bool = False) -> Tuple[str, int]:
    """Unescape \\n \\t \\" \\\\ in *raw*.

    When *stop_at_quote* is True, parsing stops at the first unescaped ``"``;
    returns ``(unescaped_text, index_of_closing_quote)``.
    When False, the entire string is consumed and *index* equals ``len(raw)``.
    """
    escape_map = {
        "n": "\n",
        "t": "\t",
        "\\": "\\",
        '"': '"',
    }

    out: List[str] = []
    i = 0

    while i < len(raw):
        c = raw[i]
        if stop_at_quote and c == '"':
            return "".join(out), i

        if c == "\\" and i + 1 < len(raw):
            nxt = raw[i + 1]
            if nxt in escape_map:
                out.append(escape_map[nxt])
                i += 2
                continue
            # Unknown escape: keep the backslash verbatim, and let the next char
            # be processed in the next iteration (same behavior as before).
            out.append("\\")
            i += 1
            continue

        out.append(c)
        i += 1
    return "".join(out), i


def _unescape_rc_value(raw: str) -> str:
    """Unescape \\n \\t \\" \\\\ inside an rc value body (no outer quotes)."""
    text, _ = _unescape(raw)
    return text


def _parse_double_quoted_line(s: str) -> str:
    """Parse a full line value that starts with ``"``; ends at last unescaped ``"``."""
    if not s.startswith('"'):
        return _unescape_rc_value(s)
    text, end = _unescape(s[1:], stop_at_quote=True)
    # end is relative to s[1:], so actual index in s is end + 1
    close_idx = end + 1
    if close_idx != len(s) - 1:
        raise ValueError("unexpected characters after closing quote")
    return text


def _redis_shard_enabled(values: Dict[str, str]) -> bool:
    """When false, omit redis harvester (no redis shard). Value must be set in rc."""
    raw = values.get("PROBE_REDIS_SHARD_ENABLED", "").strip()
    if not raw:
        sys.stderr.write("missing rc key: PROBE_REDIS_SHARD_ENABLED\n")
        sys.exit(1)

    v = raw.lower()
    return v not in ("0", "false", "no", "off")


def _resolve_rc_relative_path(rc_path: Path, rel: str) -> Path:
    rel = rel.strip()
    p = Path(rel)
    if p.is_absolute():
        return p
    cand = rc_path.parent / p
    if cand.is_file():
        return cand

    fallback = Path.cwd() / p
    sys.stderr.write(
        "warning: {} not found relative to rc, falling back to cwd: {}\n".format(cand, fallback)
    )
    return fallback


def _placeholder_replace(m: Match, values: Dict[str, str]) -> str:
    key = m.group(1)
    return values[key] if key in values else m.group(0)


def _apply_shard_block(
    values: Dict[str, str],
    rc_path: Path,
    file_key: str,
    block_key: str,
    default_rel: str,
    err_label: str,
    prefix: str = "",
) -> None:
    """Load a shard YAML snippet, render placeholders, and store in *values*."""
    rel = values.get(file_key, "").strip() or default_rel
    path = _resolve_rc_relative_path(rc_path, rel)
    if not path.is_file():
        sys.stderr.write("{} not found: {}\n".format(err_label, path))
        sys.exit(1)

    text = path.read_text(encoding="utf-8").rstrip("\n")
    values[block_key] = prefix + render_template(text, values)


if __name__ == "__main__":
    main()
