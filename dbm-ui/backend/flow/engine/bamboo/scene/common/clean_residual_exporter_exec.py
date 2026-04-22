# -*- coding: utf-8 -*-
from __future__ import print_function

import glob
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from optparse import OptionParser

# This script is intentionally written with Python 2.6-compatible syntax,
# so the same code can run on both legacy hosts (python2.x)
# and newer hosts (python3.x).
#
# What this script cleans:
# - legacy leftovers from older environments, specifically:
#   - lingering `prome_node_exporter` process (if present)
#   - root crontab entries that contain `/proc/sys/vm/drop_caches`
# - residual exporter processes
# - exporter-related plugin directories and prometheus sub-config files
# - stale entries in the GSE `.proc` file
#
# What this script may trigger after cleanup:
# - `gse_agent --restart` when `.proc` is changed
# - `bkmonitorbeat` reload when prometheus sub-config is changed


EXPORTER_NAME_REGEX = re.compile(r"\b(dbm_[A-Za-z0-9_]*_exporter)\b")
EXPORTER_NAME_LINE_REGEX = re.compile(r'^\s*name\s*:\s*["\']?(dbm_[A-Za-z0-9_]*_exporter)["\']?\s*$', re.IGNORECASE)


def to_text(value):
    # Normalize bytes/str-like values to plain text across py2/py3.
    if value is None:
        return ""
    try:
        if isinstance(value, bytes):
            return value.decode("utf-8", "ignore")
    except Exception:
        pass
    try:
        return str(value)
    except Exception:
        return ""


def log_info(msg):
    print("level=info " + to_text(msg))


def log_warn(msg):
    print("level=warn " + to_text(msg))


def log_err(msg):
    sys.stderr.write("level=error " + to_text(msg) + "\n")


def run_cmd(cmd):
    # Execute command and return (exit_code, merged_stdout_stderr_text).
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = proc.communicate()
    return proc.returncode, to_text(out) + to_text(err)


def parse_bool(name, value):
    # Accept only strict "true"/"false" string values.
    if value in ("true", "false"):
        return value == "true"
    raise ValueError("invalid_bool name=%s value=%s" % (name, value))


def is_exporter_name(name):
    return bool(EXPORTER_NAME_REGEX.match(to_text(name)))


def discover_all_exporters(base_dir):
    # Discover all possible exporter names from running processes,
    # .proc metadata, and exporter plugin directory names.
    names = set()

    rc, out = run_cmd("ps -eo args")
    if rc == 0:
        for line in out.splitlines():
            for matched in EXPORTER_NAME_REGEX.findall(line):
                names.add(matched)

    proc_file = os.path.join(base_dir, "agent", "etc", ".proc")
    if os.path.isfile(proc_file):
        try:
            root = load_json(proc_file)
            proc = root.get("proc")
            if isinstance(proc, list):
                for item in proc:
                    if isinstance(item, dict):
                        proc_name = to_text(item.get("procName", "")).strip()
                        if is_exporter_name(proc_name):
                            names.add(proc_name)
        except Exception:
            pass

    pattern = os.path.join(base_dir, "external_plugins", "sub_*_service_*", "dbm_*_exporter")
    for path in glob.glob(pattern):
        base_name = os.path.basename(path)
        if is_exporter_name(base_name):
            names.add(base_name)

    return sorted(names)


def ensure_path_under_base_dir(base_dir, target):
    # Guard against accidental path traversal or root-path deletion.
    abs_base = os.path.realpath(base_dir)
    abs_target = os.path.realpath(target)
    if not abs_target or abs_target == "/":
        raise ValueError("invalid_target_path target=%s" % target)
    if abs_target == abs_base or abs_target.startswith(abs_base + os.sep):
        return abs_target
    raise ValueError("path_outside_base_dir base_dir=%s target=%s" % (abs_base, abs_target))


def load_json(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path, data):
    with io.open(path, "w", encoding="utf-8") as f:
        text = json.dumps(data, ensure_ascii=False, indent=2)
        f.write(to_text(text))


def clean_legacy_residual(dry_run):
    # Cleanup historical leftovers:
    # - kill prome_node_exporter process if exists
    # - remove drop_caches cron entries from root crontab
    rc, out = run_cmd("ps -eo pid,args")
    pids = []
    if rc == 0:
        for line in out.splitlines():
            line = line.strip()
            if "prome_node_exporter" in line and "awk" not in line:
                items = line.split(None, 1)
                if items:
                    pids.append(items[0])
    pid_str = " ".join(pids)
    log_info('step=legacy_clean dry_run=%s prome_node_exporter_pids="%s"' % ("true" if dry_run else "false", pid_str))
    if pids and not dry_run:
        run_cmd("kill -9 %s >/dev/null 2>&1 || true" % " ".join(pids))

    rc, crontab_text = run_cmd("crontab -u root -l 2>/dev/null")
    rows = []
    if rc == 0:
        for idx, line in enumerate(crontab_text.splitlines()):
            if "/proc/sys/vm/drop_caches" in line:
                rows.append("%d:%s" % (idx + 1, line))
    row_text = "\\n".join(rows)
    log_info('step=legacy_clean dry_run=%s drop_caches_rows="%s"' % ("true" if dry_run else "false", row_text))
    if rows and not dry_run:
        keep_lines = []
        for line in crontab_text.splitlines():
            if "/proc/sys/vm/drop_caches" not in line:
                keep_lines.append(line)
        fd, tmp = tempfile.mkstemp(prefix="dbm_clean_residual_", text=True)
        os.close(fd)
        with io.open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(keep_lines) + ("\n" if keep_lines else ""))
        try:
            rc2, out2 = run_cmd("crontab -u root %s" % tmp)
            if rc2 != 0:
                raise RuntimeError(out2)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


def scan_exporter_pids_in_base_dir(exporters, base_dir):
    # Scan process list and keep only exporter pids whose /proc/<pid>/exe dir is under base_dir.
    matched = {}
    for name in exporters:
        matched[name] = []

    rc, out = run_cmd("ps -eo pid,args")
    if rc != 0:
        log_warn("step=scan_exporter_pid result=ps_failed detail=%s" % out.strip())
        return matched

    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        items = line.split(None, 1)
        if len(items) < 2:
            continue
        pid = items[0].strip()
        args = items[1]
        if not pid.isdigit():
            continue
        for name in exporters:
            if name not in args:
                continue
            try:
                exe_path = os.readlink("/proc/%s/exe" % pid)
            except OSError:
                log_info("step=scan_exporter_pid exporter=%s pid=%s result=skip_no_exe" % (name, pid))
                continue
            exe_dir = os.path.dirname(exe_path)
            try:
                ensure_path_under_base_dir(base_dir, exe_dir)
            except Exception:
                log_info(
                    "step=scan_exporter_pid exporter=%s pid=%s exe_dir=%s result=skip_outside_base_dir"
                    % (name, pid, exe_dir)
                )
                continue
            matched[name].append(pid)
    return matched


def kill_exporters(exporters, base_dir, dry_run):
    # Kill target exporter processes by PID with exe-dir guard.
    if not exporters:
        log_info("step=kill_exporter dry_run=%s result=skip_empty_exporters" % ("true" if dry_run else "false"))
        return

    pid_map = scan_exporter_pids_in_base_dir(exporters, base_dir)
    for name in exporters:
        pids = pid_map.get(name, [])
        if not pids:
            log_info(
                "step=kill_exporter dry_run=%s exporter=%s result=no_process_found"
                % ("true" if dry_run else "false", name)
            )
            continue
        for pid in pids:
            if dry_run:
                log_info(
                    'step=kill_exporter dry_run=true exporter=%s pid=%s command="kill -9 %s" result=skip'
                    % (name, pid, pid)
                )
                continue
            rc, out = run_cmd("kill -9 %s" % pid)
            if rc != 0:
                log_info(
                    "step=kill_exporter dry_run=false exporter=%s pid=%s result=no_process_found detail=%s"
                    % (name, pid, out.strip())
                )
                continue
            log_info("step=kill_exporter dry_run=false exporter=%s pid=%s result=success" % (name, pid))


def remove_exporter_dirs(base_dir, exporters, dry_run):
    # Remove exporter plugin directories under external_plugins.
    for name in exporters:
        pattern = os.path.join(base_dir, "external_plugins", "sub_*_service_*", name)
        for path in glob.glob(pattern):
            abs_path = ensure_path_under_base_dir(base_dir, path)
            parent_dir = os.path.dirname(abs_path)
            if dry_run:
                log_info("step=remove_exporter_dir dry_run=true path=%s result=skip" % abs_path)
                if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                    log_info("step=remove_exporter_parent_dir dry_run=true path=%s result=skip" % parent_dir)
            else:
                if os.path.isdir(abs_path):
                    run_cmd("rm -rf %s" % abs_path)
                log_info("step=remove_exporter_dir dry_run=false path=%s result=success" % abs_path)
                # Best-effort cleanup for leftover empty sub_*_service_* directory.
                if os.path.isdir(parent_dir):
                    try:
                        ensure_path_under_base_dir(base_dir, parent_dir)
                        if not os.listdir(parent_dir):
                            os.rmdir(parent_dir)
                            log_info(
                                "step=remove_exporter_parent_dir dry_run=false path=%s result=success" % parent_dir
                            )
                    except Exception:
                        log_info("step=remove_exporter_parent_dir dry_run=false path=%s result=skip" % parent_dir)


def remove_empty_exporter_parent_dirs(base_dir, dry_run):
    # Remove empty sub_*_service_* directories even when no exporter child matched this round.
    pattern = os.path.join(base_dir, "external_plugins", "sub_*_service_*")
    for parent_dir in glob.glob(pattern):
        abs_parent_dir = ensure_path_under_base_dir(base_dir, parent_dir)
        if not os.path.isdir(abs_parent_dir):
            continue
        try:
            is_empty = not os.listdir(abs_parent_dir)
        except Exception:
            log_info(
                "step=remove_exporter_parent_dir dry_run=%s path=%s result=skip"
                % ("true" if dry_run else "false", abs_parent_dir)
            )
            continue
        if not is_empty:
            continue
        if dry_run:
            log_info("step=remove_exporter_parent_dir dry_run=true path=%s result=skip" % abs_parent_dir)
            continue
        try:
            os.rmdir(abs_parent_dir)
            log_info("step=remove_exporter_parent_dir dry_run=false path=%s result=success" % abs_parent_dir)
        except Exception:
            log_info("step=remove_exporter_parent_dir dry_run=false path=%s result=skip" % abs_parent_dir)


def remove_prometheus_sub_configs(base_dir, exporters, dry_run):
    # Remove prometheus sub-config files only when:
    # 1) file name matches bkmonitorbeat_prometheus_sub_*.conf
    # 2) file contains a line like: name: dbm_xxx_exporter
    changed = False
    pattern = os.path.join(base_dir, "plugins", "etc", "bkmonitorbeat", "bkmonitorbeat_prometheus_sub_*.conf")
    for file_path in glob.glob(pattern):
        if not file_path.endswith(".conf"):
            continue
        abs_path = ensure_path_under_base_dir(base_dir, file_path)
        try:
            with io.open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            content = ""
        has_exporter_name_line = False
        for line in content.splitlines():
            line_match = EXPORTER_NAME_LINE_REGEX.match(line)
            if not line_match:
                continue
            exporter_name = line_match.group(1)
            if exporters and exporter_name not in exporters:
                continue
            has_exporter_name_line = True
            break
        if not has_exporter_name_line:
            continue
        changed = True
        if dry_run:
            log_info("step=remove_prometheus_sub_config dry_run=true path=%s result=skip" % abs_path)
        else:
            if os.path.exists(abs_path):
                os.remove(abs_path)
            log_info("step=remove_prometheus_sub_config dry_run=false path=%s result=success" % abs_path)
    return changed


def clean_stale_proc_file(base_dir, exporters, dry_run):
    # Remove stale .proc entries where setupPath no longer exists.
    proc_file = os.path.join(base_dir, "agent", "etc", ".proc")
    if not os.path.isfile(proc_file):
        log_info(
            "step=proc_clean dry_run=%s changed=false removed=[] result=skip_no_file"
            % ("true" if dry_run else "false")
        )
        return False
    proc_file = ensure_path_under_base_dir(base_dir, proc_file)

    try:
        root = load_json(proc_file)
    except Exception as err:
        raise RuntimeError(
            "step=proc_clean dry_run=%s result=failed detail=read_or_parse_failed:%s"
            % ("true" if dry_run else "false", err)
        )

    proc = root.get("proc")
    if proc is None:
        log_info("step=proc_clean dry_run=%s changed=false removed=[] result=done" % ("true" if dry_run else "false"))
        return False
    if not isinstance(proc, list):
        log_warn(
            "step=proc_clean dry_run=%s changed=false removed=[] result=skip_unsupported_schema"
            % ("true" if dry_run else "false")
        )
        return False

    new_proc = []
    removed = []
    for item in proc:
        if not isinstance(item, dict):
            new_proc.append(item)
            continue
        proc_name = to_text(item.get("procName", "")).strip()
        setup_path = to_text(item.get("setupPath", "")).strip()
        if proc_name not in exporters:
            new_proc.append(item)
            continue
        if not setup_path:
            new_proc.append(item)
            continue
        if not os.path.exists(setup_path):
            removed.append(proc_name)
            continue
        new_proc.append(item)

    changed = bool(removed)
    if changed and not dry_run:
        root["proc"] = new_proc
        dump_json(proc_file, root)
    log_info(
        "step=proc_clean dry_run=%s changed=%s removed=[%s] result=done"
        % ("true" if dry_run else "false", "true" if changed else "false", ",".join(removed))
    )
    return changed


def restart_gse_if_needed(base_dir, proc_changed, dry_run):
    # Restart gse_agent only when .proc content was changed in non-dry-run mode.
    if (not proc_changed) or dry_run:
        log_info(
            "step=gse_restart dry_run=%s changed=%s result=skip"
            % ("true" if dry_run else "false", "1" if proc_changed else "0")
        )
        return
    gse_bin = os.path.join(base_dir, "agent", "bin", "gse_agent")
    if not (os.path.exists(gse_bin) and os.access(gse_bin, os.X_OK)):
        gse_bin = "/usr/local/gse2_bkte/agent/bin/gse_agent"
    rc, out = run_cmd("%s --restart" % gse_bin)
    if rc != 0:
        log_warn('step=gse_restart dry_run=false changed=1 result=warning detail="%s"' % out.strip())
        return
    log_info("step=gse_restart dry_run=false changed=1 result=success")


def reload_bkmonitorbeat_if_needed(base_dir, prometheus_changed, dry_run, enable_reload):
    # Reload bkmonitorbeat when prometheus config changed and reload is enabled.
    if (not prometheus_changed) or dry_run or (not enable_reload):
        log_info(
            "step=reload_bkmonitorbeat dry_run=%s changed=%s enabled=%s result=skip"
            % (
                "true" if dry_run else "false",
                "1" if prometheus_changed else "0",
                "true" if enable_reload else "false",
            )
        )
        return
    reload_script = os.path.join(base_dir, "plugins", "bin", "reload.sh")
    if not os.path.isfile(reload_script):
        log_warn("step=reload_bkmonitorbeat dry_run=false result=skip_no_script path=%s" % reload_script)
        return
    cmd = "bash %s" % reload_script
    rc, out = run_cmd(cmd)
    if rc != 0:
        raise RuntimeError('step=reload_bkmonitorbeat dry_run=false result=failed detail="%s"' % out.strip())
    log_info("step=reload_bkmonitorbeat dry_run=false result=success")


def build_parser():
    # Keep option parser for Python 2.6 compatibility.
    parser = OptionParser()
    parser.add_option("--base-dir", dest="base_dir", default="/usr/local/gse2_bkte")
    parser.add_option("--exporters", dest="exporters", default="")
    parser.add_option("--dry-run", dest="dry_run", default="false")
    parser.add_option("--enable-legacy-clean", dest="enable_legacy_clean", default="true")
    parser.add_option("--enable-reload", dest="enable_reload", default="true")
    return parser


def main():
    # Main flow: validate input -> cleanup -> optional restart/reload.
    parser = build_parser()
    options, _args = parser.parse_args()

    try:
        dry_run = parse_bool("dry_run", options.dry_run)
        enable_legacy_clean = parse_bool("enable_legacy_clean", options.enable_legacy_clean)
        enable_reload = parse_bool("enable_reload", options.enable_reload)
    except Exception as err:
        log_err(to_text(err))
        return 1

    base_dir = os.path.realpath(to_text(options.base_dir).strip())
    if not base_dir or base_dir == "/":
        log_err("msg=invalid_base_dir base_dir=%s" % base_dir)
        return 1

    exporters_text = to_text(options.exporters).strip()
    configured_exporters = [x.strip() for x in exporters_text.split(",") if x.strip()]
    for name in configured_exporters:
        if not is_exporter_name(name):
            log_err("msg=invalid_exporter_name exporter=%s" % name)
            return 1
    discovered_exporters = discover_all_exporters(base_dir)
    exporters = sorted(set(configured_exporters).union(set(discovered_exporters)))
    log_info(
        "step=discover_exporters configured=[%s] discovered=[%s] merged=[%s]"
        % (",".join(configured_exporters), ",".join(discovered_exporters), ",".join(exporters))
    )

    log_info(
        "step=start dry_run=%s base_dir=%s exporters=%s"
        % ("true" if dry_run else "false", base_dir, ",".join(exporters))
    )
    try:
        if enable_legacy_clean:
            clean_legacy_residual(dry_run)
        else:
            log_info("step=legacy_clean dry_run=%s result=skip_disabled" % ("true" if dry_run else "false"))
        kill_exporters(exporters, base_dir, dry_run)
        remove_exporter_dirs(base_dir, exporters, dry_run)
        remove_empty_exporter_parent_dirs(base_dir, dry_run)
        prometheus_changed = remove_prometheus_sub_configs(base_dir, exporters, dry_run)
        proc_changed = clean_stale_proc_file(base_dir, exporters, dry_run)
        restart_gse_if_needed(base_dir, proc_changed, dry_run)
        reload_bkmonitorbeat_if_needed(base_dir, prometheus_changed, dry_run, enable_reload)
    except Exception as err:
        log_err(to_text(err))
        return 1
    log_info("step=finish result=success")
    return 0


if __name__ == "__main__":
    sys.exit(main())
