#!/bin/sh
# -*- coding: utf-8 -*-
# MIT License - same as dbha-v2 module
# Compare probe YAML. Usage: -l/--left with either -r/--right or --admin-endpoints.
# Polyglot: sh picks python, python3, or python2; the interpreter skips this block.
""":"
for py in python python3 python2; do
	command -v "$py" >/dev/null 2>&1 || continue
	exec "$py" "$0" "$@"
done
echo "compare_probe_config.py: need python, python3 or python2 in PATH" >&2
exit 2
"""
from __future__ import print_function

import argparse
import errno
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time

EXIT_EQUAL = 0
EXIT_DIFF = 1
EXIT_ERROR = 2

HEALTH_TIMEOUT_SEC = 10
DEFAULT_GENCONFIG_TIMEOUT = "30s"
GENCONFIG_LABEL = "gen-config"
CRON_MARKER = "DBHA_V2_PROBE_GUARD"
CRON_LOG_NAME = "dbha-v2-probe-cron.log"
KIND_GUARD = "guard"
KIND_WORKER = "worker"
KIND_SKIP = "skip"

DIFF_ONLY_LEFT = "only-left"
DIFF_ONLY_RIGHT = "only-right"
DIFF_VALUE = "value"

# Side names per mode. Offline (-r) keeps left/right, which match the flags. The admin
# path compares gen-config output against the -l file, so left/right would contradict the
# flag names there.
LABELS_OFFLINE = ("left", "right")
LABELS_ADMIN = ("expected", "local")

# Error blocks print a path plus Error / Hint / Usage / Example; "Example:" is the longest label.
ERROR_FIELD_WIDTH = 9
USAGE_ADMIN_ARGS = "-l etc/probe.yaml --admin-endpoints <host:port[;...]> [options]"
USAGE_OFFLINE_ARGS = "-l etc/probe.yaml -r <other.yaml> [options]"
EXAMPLE_ADMIN_ARGS = "-l etc/probe.yaml --admin-endpoints 127.0.0.1:19001"
EXAMPLE_OFFLINE_ARGS = "-l etc/probe.yaml -r /tmp/probe-from-admin.yaml"
HINT_SEE_HELP = "run with -h to see every option"
OPTION_HINTS = {
    "-l/--left": "pass the local probe YAML, e.g. -l etc/probe.yaml",
    "-r/--right": "-r takes a second YAML file for offline compare",
    "--admin-endpoints": "--admin-endpoints takes admin host:port, join several with ;",
    "--cloud-id": "--cloud-id takes bk_cloud_id as a non-negative integer (default: 0)",
    "--timeout": "--timeout takes a duration such as 30s, 1m, 500ms or plain seconds",
    "-b/--bin": "-b takes the probe binary path (default: <install-root>/bin/dbha-probe)",
}

REPORT_WIDTH = 64
REPORT_SEPARATOR = "-" * REPORT_WIDTH
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_CYAN = "\033[36m"
_COLOR_ENABLED = False

_PY2 = sys.version_info[0] < 3
if _PY2:
    _INT_TYPES = (int, long)  # noqa: F821
    _TEXT_TYPES = (str, unicode)  # noqa: F821
else:
    _INT_TYPES = (int,)
    _TEXT_TYPES = (str,)


class LoadError(Exception):
    """Failed to read or parse a YAML file."""


def is_mapping(value):
    return isinstance(value, dict)


def is_sequence(value):
    if isinstance(value, _TEXT_TYPES):
        return False
    if isinstance(value, bytes):
        return False
    return isinstance(value, (list, tuple))


def is_number(value):
    if isinstance(value, bool):
        return False
    return isinstance(value, _INT_TYPES) or isinstance(value, float)


def to_text(value):
    if _PY2:
        if isinstance(value, unicode):  # noqa: F821
            return value
        if isinstance(value, str):
            return value.decode("utf-8")
        return unicode(value)  # noqa: F821
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def numeric_text(value):
    if isinstance(value, float) and value == int(value):
        try:
            return u"%d" % int(value)
        except (OverflowError, ValueError):
            pass
    if isinstance(value, _INT_TYPES) and not isinstance(value, bool):
        return u"%d" % value
    return to_text(value)


def scalar_canon(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "t:true" if value else "t:false"
    if is_number(value):
        return "t:" + numeric_text(value)
    return "t:" + to_text(value)


def canon(value):
    if is_mapping(value):
        idx = key_index(value)
        parts = []
        for text_key in sorted(idx.keys()):
            parts.append(text_key + ":" + canon(value[idx[text_key]]))
        return "{" + ",".join(parts) + "}"
    if is_sequence(value):
        parts = sorted(canon(item) for item in value)
        return "[" + ",".join(parts) + "]"
    return scalar_canon(value)


def key_index(mapping):
    idx = {}
    for key in mapping:
        idx[to_text(key)] = key
    return idx


def scalars_equal(left, right):
    if left is None or right is None:
        return left is None and right is None
    if is_number(left) and is_number(right):
        return left == right
    return scalar_canon(left) == scalar_canon(right)


def join_path(parent, key):
    text_key = to_text(key)
    if not parent:
        return text_key
    return parent + "." + text_key


class Diff(object):
    """One reported difference: its kind, dotted path, and the values involved."""

    def __init__(self, kind, path, left=None, right=None):
        self.kind = kind
        self.path = path
        self.left = left
        self.right = right


def is_container(value):
    return is_mapping(value) or is_sequence(value)


def walk(path, left, right, diffs, ignore_extra_right=False):
    if is_mapping(left) and is_mapping(right):
        walk_maps(path, left, right, diffs, ignore_extra_right)
        return
    if is_sequence(left) and is_sequence(right):
        walk_seqs(path, left, right, diffs, ignore_extra_right)
        return
    if is_container(left) or is_container(right):
        diffs.append(Diff(DIFF_VALUE, _path_or_root(path), left, right))
        return
    if scalars_equal(left, right):
        return
    diffs.append(Diff(DIFF_VALUE, _path_or_root(path), left, right))


def _path_or_root(path):
    if path:
        return path
    return "."


def walk_maps(path, left, right, diffs, ignore_extra_right=False):
    left_idx = key_index(left)
    right_idx = key_index(right)
    for text_key in sorted(set(left_idx.keys()) | set(right_idx.keys())):
        child = join_path(path, text_key)
        in_left = text_key in left_idx
        in_right = text_key in right_idx
        if in_left and not in_right:
            diffs.append(Diff(DIFF_ONLY_LEFT, child, left[left_idx[text_key]], None))
            continue
        if in_right and not in_left:
            if ignore_extra_right:
                continue
            diffs.append(Diff(DIFF_ONLY_RIGHT, child, None, right[right_idx[text_key]]))
            continue
        walk(
            child,
            left[left_idx[text_key]],
            right[right_idx[text_key]],
            diffs,
            ignore_extra_right,
        )


def walk_seqs(path, left, right, diffs, ignore_extra_right=False):
    unmatched_left, unmatched_right = drop_common_items(left, right)
    pairs, only_left, only_right = pair_items(unmatched_left, unmatched_right)
    for index, left_item, right_item in pairs:
        walk("%s[%d]" % (path, index), left_item, right_item, diffs, ignore_extra_right)
    for index, item in only_left:
        diffs.append(Diff(DIFF_ONLY_LEFT, "%s[%d]" % (path, index), item, None))
    for index, item in only_right:
        if ignore_extra_right:
            continue
        diffs.append(Diff(DIFF_ONLY_RIGHT, "%s[%d]" % (path, index), None, item))


def drop_common_items(left, right):
    """Remove items present on both sides, so order alone never counts as a difference."""
    pool = []
    for index, item in enumerate(right):
        pool.append((index, item, canon(item)))
    unmatched_left = []
    for index, item in enumerate(left):
        item_canon = canon(item)
        hit = None
        for entry in pool:
            if entry[2] == item_canon:
                hit = entry
                break
        if hit is None:
            unmatched_left.append((index, item))
            continue
        pool.remove(hit)
    unmatched_right = [(entry[0], entry[1]) for entry in pool]
    return unmatched_left, unmatched_right


def pair_items(unmatched_left, unmatched_right):
    """Pair leftovers with their closest counterpart, so a changed item reads as field edits."""
    pairs = []
    only_left = []
    remaining = list(unmatched_right)
    for index, item in unmatched_left:
        best = None
        best_score = 0
        for candidate in remaining:
            score = similarity(item, candidate[1])
            if score > best_score:
                best = candidate
                best_score = score
        if best is None:
            only_left.append((index, item))
            continue
        remaining.remove(best)
        pairs.append((index, item, best[1]))
    return pairs, only_left, remaining


def similarity(left, right):
    if is_mapping(left) and is_mapping(right):
        left_idx = key_index(left)
        right_idx = key_index(right)
        score = 0
        for text_key in set(left_idx.keys()) & set(right_idx.keys()):
            if canon(left[left_idx[text_key]]) == canon(right[right_idx[text_key]]):
                score += 2
            else:
                score += 1
        return score
    if is_sequence(left) and is_sequence(right):
        return 1
    if is_container(left) or is_container(right):
        return 0
    return 1


def needs_quotes(text):
    if text == "" or text != text.strip():
        return True
    if text.endswith(":"):
        return True
    for hint in ("#", ": ", "\n", "\t"):
        if hint in text:
            return True
    return False


def format_scalar(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if is_number(value):
        return numeric_text(value)
    text = to_text(value)
    if needs_quotes(text):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def format_inline(value):
    if is_mapping(value):
        return "{}"
    if is_sequence(value):
        return "[]"
    return format_scalar(value)


def format_block(value, indent):
    pad = " " * indent
    if is_mapping(value):
        if not value:
            return [pad + "{}"]
        lines = []
        idx = key_index(value)
        for text_key in sorted(idx.keys()):
            child = value[idx[text_key]]
            if is_container(child) and child:
                lines.append(pad + text_key + ":")
                lines.extend(format_block(child, indent + 2))
            elif text_key.lower() == "password":
                lines.append(pad + text_key + ": ***")
            else:
                lines.append(pad + text_key + ": " + format_inline(child))
        return lines
    if is_sequence(value):
        if not value:
            return [pad + "[]"]
        lines = []
        for item in value:
            if is_container(item) and item:
                block = format_block(item, indent + 2)
                lines.append(pad + "- " + block[0].strip())
                lines.extend(block[1:])
            else:
                lines.append(pad + "- " + format_inline(item))
        return lines
    return [pad + format_scalar(value)]


def redact_secrets(value):
    if is_mapping(value):
        out = {}
        idx = key_index(value)
        for text_key in idx:
            child = value[idx[text_key]]
            if text_key.lower() == "password":
                out[text_key] = "***"
            else:
                out[text_key] = redact_secrets(child)
        return out
    if is_sequence(value):
        return [redact_secrets(item) for item in value]
    return value


def enable_color(no_color=False, stream=None):
    target = stream or sys.stdout
    is_tty = getattr(target, "isatty", lambda: False)()
    return (
        not no_color
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM", "").lower() != "dumb"
        and is_tty
    )


def configure_color(no_color=False, stream=None):
    global _COLOR_ENABLED
    _COLOR_ENABLED = enable_color(no_color, stream)


def paint(text, style):
    if not _COLOR_ENABLED:
        return text
    return style + text + ANSI_RESET


def status_style(status):
    if status == "PASSED" or status == "PASS":
        return ANSI_GREEN
    if status == "FAILED" or status == "FAIL" or status == "ERROR":
        return ANSI_RED
    return ANSI_YELLOW


def section_header(title, status=None):
    text = title if status is None else "%s: %s" % (title, status)
    line = "=== " + text + " "
    line += "=" * max(1, REPORT_WIDTH - len(line))
    style = ANSI_BOLD
    if status is not None:
        style += status_style(status)
    return paint(line, style)


def render_field(label, text, width=6, style=None):
    padded = "%-*s" % (width, label + ":")
    if style:
        padded = paint(padded, style)
    return "    %s %s" % (padded, text)


def field_width(labels):
    return max(12, len(labels[0]) + 1, len(labels[1]) + 1)


def diff_title(kind, labels):
    if labels == LABELS_ADMIN:
        if kind == DIFF_ONLY_LEFT:
            return "MISSING LOCALLY"
        if kind == DIFF_ONLY_RIGHT:
            return "EXTRA LOCALLY"
        return "VALUE MISMATCH"
    if kind == DIFF_ONLY_LEFT:
        return "ONLY IN LEFT"
    if kind == DIFF_ONLY_RIGHT:
        return "ONLY IN RIGHT"
    return "VALUE MISMATCH"


def render_side(label, value, width):
    if is_container(value) and value:
        lines = ["    %s" % paint(label.capitalize() + ":", ANSI_CYAN)]
        lines.extend(format_block(value, 6))
        return lines
    return [render_field(label.capitalize(), format_inline(value), width, ANSI_CYAN)]


def render_diff(number, total, diff, labels, width):
    left = redact_secrets(diff.left)
    right = redact_secrets(diff.right)
    title = diff_title(diff.kind, labels)
    style = ANSI_RED if diff.kind == DIFF_VALUE else ANSI_YELLOW
    lines = [paint("[%d/%d] %s" % (number, total, title), ANSI_BOLD + style)]
    lines.append(render_field("Path", diff.path, width, ANSI_CYAN))
    secret_path = "password" in diff.path.lower()
    if diff.kind != DIFF_ONLY_RIGHT:
        if secret_path and not is_container(left):
            left = "***"
        lines.extend(render_side(labels[0], left, width))
    if diff.kind != DIFF_ONLY_LEFT:
        if secret_path and not is_container(right):
            right = "***"
        lines.extend(render_side(labels[1], right, width))
    return lines


def emit(line, stream=None):
    """Print a line, tolerating a non-UTF-8 terminal on Python 2."""
    target = stream or sys.stdout
    if _PY2 and isinstance(line, unicode):  # noqa: F821
        line = line.encode("utf-8", "replace")
    print(line, file=target)


def render_config_report(diffs, left_path, right_path, labels, error=None):
    width = field_width(labels)
    status = "ERROR" if error else ("FAILED" if diffs else "PASSED")
    lines = [section_header("PROBE CONFIG CHECK", status)]
    lines.append(render_field(labels[0].capitalize(), left_path, width, ANSI_CYAN))
    lines.append(render_field(labels[1].capitalize(), right_path, width, ANSI_CYAN))
    lines.append(render_field("Differences", str(len(diffs)), width))
    if error:
        lines.append(render_field("Error", error, width, ANSI_RED))
        return lines
    if not diffs:
        return lines
    for number, diff in enumerate(diffs, 1):
        lines.append("")
        lines.extend(render_diff(number, len(diffs), diff, labels, width))
        if number != len(diffs):
            lines.append(REPORT_SEPARATOR)
    return lines


def _is_comment_or_blank(stripped):
    return (not stripped) or stripped.startswith("#")


def _document_count(text):
    docs = 0
    implicit = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped == "---":
            docs += 1
            implicit = True
            continue
        if stripped == "..." or _is_comment_or_blank(stripped):
            continue
        if not implicit and docs == 0:
            docs = 1
            implicit = True
    return docs


def _strip_inline_comment(text):
    in_single = False
    in_double = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_single:
            if ch == "'" and i + 1 < len(text) and text[i + 1] == "'":
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            if ch == "\\" and i + 1 < len(text):
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue
        if ch == "'":
            in_single = True
        elif ch == '"':
            in_double = True
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
        i += 1
    return text.rstrip()


def _split_map_pair(text):
    in_single = False
    in_double = False
    i = 0
    while i < len(text):
        ch = text[i]
        if in_single:
            if ch == "'" and i + 1 < len(text) and text[i + 1] == "'":
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            if ch == "\\" and i + 1 < len(text):
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue
        if ch == "'":
            in_single = True
        elif ch == '"':
            in_double = True
        elif ch == ":":
            if i + 1 >= len(text) or text[i + 1] in " \t":
                key = text[:i].strip()
                val = text[i + 1 :].strip()
                return key, val
        i += 1
    return None, None


def _unquote(raw):
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        inner = raw[1:-1]
        if raw[0] == "'":
            return inner.replace("''", "'")
        return (
            inner.replace("\\\\", "\\")
            .replace("\\\"", '"')
            .replace("\\n", "\n")
            .replace("\\t", "\t")
        )
    return None


def _parse_scalar(raw):
    raw = raw.strip()
    quoted = _unquote(raw)
    if quoted is not None:
        return quoted
    if raw == "[]":
        return []
    if raw == "{}":
        return {}
    if raw in ("~", "null", "Null", "NULL"):
        return None
    if raw in ("true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"):
        return True
    if raw in ("false", "False", "FALSE", "no", "No", "NO", "off", "Off", "OFF"):
        return False
    if raw.startswith("[") and raw.endswith("]"):
        return _parse_flow_seq(raw[1:-1])
    if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
        try:
            return int(raw)
        except ValueError:
            pass
    if "." in raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return raw


def _parse_flow_seq(inner):
    inner = inner.strip()
    if not inner:
        return []
    items = []
    buf = []
    in_single = False
    in_double = False
    i = 0
    while i < len(inner):
        ch = inner[i]
        if in_single:
            buf.append(ch)
            if ch == "'" and i + 1 < len(inner) and inner[i + 1] == "'":
                buf.append(inner[i + 1])
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(inner):
                buf.append(inner[i + 1])
                i += 2
                continue
            if ch == '"':
                in_double = False
            i += 1
            continue
        if ch == "'":
            in_single = True
            buf.append(ch)
        elif ch == '"':
            in_double = True
            buf.append(ch)
        elif ch == ",":
            items.append(_parse_scalar("".join(buf)))
            buf = []
        else:
            buf.append(ch)
        i += 1
    items.append(_parse_scalar("".join(buf)))
    return items


def _tokenize(text, path):
    rows = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[: len(raw) - len(raw.lstrip(" \t"))]:
            raise LoadError("yaml parse failed, path: %s, errmsg: tabs in indent" % path)
        stripped = raw.strip()
        if stripped in ("---", "...") or _is_comment_or_blank(stripped):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = _strip_inline_comment(raw[indent:])
        if not content:
            continue
        rows.append((lineno, indent, content))
    return rows


class _YamlParser(object):
    def __init__(self, text, path):
        self.path = path
        self.rows = _tokenize(text, path)
        self.i = 0

    def _fail(self, errmsg, lineno=None):
        if lineno is None and self.i < len(self.rows):
            lineno = self.rows[self.i][0]
        if lineno is None:
            raise LoadError("yaml parse failed, path: %s, errmsg: %s" % (self.path, errmsg))
        raise LoadError(
            "yaml parse failed, path: %s, line: %s, errmsg: %s"
            % (self.path, lineno, errmsg)
        )

    def _peek(self):
        if self.i >= len(self.rows):
            return None
        return self.rows[self.i]

    def parse_root(self):
        if not self.rows:
            raise LoadError("empty yaml, path: %s" % self.path)
        lineno, indent, content = self.rows[0]
        if content.startswith("-"):
            raise LoadError("yaml root must be a mapping, path: %s" % self.path)
        if _split_map_pair(content)[0] is None:
            raise LoadError("yaml root must be a mapping, path: %s" % self.path)
        root = self._parse_map(indent)
        if self.i < len(self.rows):
            self._fail("unexpected content after mapping")
        if not is_mapping(root):
            raise LoadError("yaml root must be a mapping, path: %s" % self.path)
        return root

    def _parse_map(self, indent):
        result = {}
        while True:
            row = self._peek()
            if row is None:
                break
            lineno, line_indent, content = row
            if line_indent < indent:
                break
            if line_indent > indent:
                self._fail("unexpected indent", lineno)
            if content.startswith("-") and (len(content) == 1 or content[1] in " \t"):
                self._fail("sequence where mapping expected", lineno)
            key, rest = _split_map_pair(content)
            if key is None or key == "":
                self._fail("expected key:", lineno)
            self.i += 1
            result[key] = self._parse_value(rest, indent, lineno)
        return result

    def _parse_value(self, rest, parent_indent, lineno):
        if rest != "":
            return _parse_scalar(rest)
        nxt = self._peek()
        if nxt is None or nxt[1] < parent_indent:
            return None
        child_indent = nxt[1]
        child = nxt[2]
        is_dash = child.startswith("-") and (len(child) == 1 or child[1] in " \t")
        # Compact lists put "-" at the same indent as the key (PyYAML dump).
        if is_dash and child_indent >= parent_indent:
            return self._parse_list(child_indent)
        if child_indent > parent_indent:
            return self._parse_map(child_indent)
        return None

    def _parse_list(self, dash_indent):
        items = []
        while True:
            row = self._peek()
            if row is None:
                break
            lineno, line_indent, content = row
            if line_indent < dash_indent:
                break
            if line_indent > dash_indent:
                self._fail("unexpected indent", lineno)
            if not (content.startswith("-") and (len(content) == 1 or content[1] in " \t")):
                break
            rest = content[1:].strip()
            self.i += 1
            items.append(self._parse_list_item(rest, dash_indent, lineno))
        return items

    def _parse_list_item(self, rest, dash_indent, lineno):
        if rest == "":
            nxt = self._peek()
            if nxt is None or nxt[1] <= dash_indent:
                return None
            if nxt[2].startswith("-") and nxt[1] > dash_indent:
                return self._parse_list(nxt[1])
            return self._parse_map(nxt[1])
        key, val = _split_map_pair(rest)
        if key is None:
            return _parse_scalar(rest)
        item = {key: self._parse_value(val, dash_indent, lineno)}
        nxt = self._peek()
        if nxt is not None and nxt[1] > dash_indent:
            if not (nxt[2].startswith("-") and (len(nxt[2]) == 1 or nxt[2][1] in " \t")):
                nested = self._parse_map(nxt[1])
                for nested_key in nested:
                    item[nested_key] = nested[nested_key]
        return item


def load_mapping(path):
    if os.path.isdir(path):
        raise LoadError("%s is a directory" % path)
    if not os.path.isfile(path):
        raise LoadError("file not found: %s" % path)
    try:
        handle = io.open(path, "r", encoding="utf-8-sig")
        try:
            text = handle.read()
        finally:
            handle.close()
    except UnicodeDecodeError as err:
        raise LoadError("decode failed, path: %s, errmsg: %s" % (path, err))
    except (IOError, OSError) as err:
        raise LoadError("cannot read path: %s, errmsg: %s" % (path, err))

    docs = _document_count(text)
    if docs == 0:
        raise LoadError("empty yaml, path: %s" % path)
    if docs > 1:
        raise LoadError("multiple yaml documents, path: %s" % path)
    try:
        root = _YamlParser(text, path).parse_root()
    except LoadError:
        raise
    except Exception as err:
        raise LoadError("yaml parse failed, path: %s, errmsg: %s" % (path, err))
    return root


def to_unicode(raw):
    if raw is None:
        return u""
    if _PY2:
        if isinstance(raw, unicode):  # noqa: F821
            return raw
        return raw.decode("utf-8", "replace")
    if isinstance(raw, bytes):
        return raw.decode("utf-8", "replace")
    return raw


def run_cmd(argv, cwd=None, timeout=HEALTH_TIMEOUT_SEC):
    """Run argv with shell=False. Returns (returncode, stdout, stderr) or timeout."""
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as err:
        if err.errno == errno.ENOENT:
            return None, u"", u"command not found: %s" % argv[0]
        return None, u"", to_unicode(str(err))
    deadline = time.time() + timeout
    while proc.poll() is None:
        if time.time() >= deadline:
            try:
                proc.kill()
            except OSError:
                pass
            proc.wait()
            return None, u"", u"timeout"
        time.sleep(0.05)
    out, err = proc.communicate()
    return proc.returncode, to_unicode(out), to_unicode(err)


def _nonempty(value):
    if value is None:
        return False
    return to_text(value).strip() != ""


def parse_cloud_id(text):
    try:
        value = int(text)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("must be an integer >= 0")
    if value < 0:
        raise argparse.ArgumentTypeError("must be an integer >= 0")
    return value


def parse_timeout_sec(text):
    raw = to_text(text).strip()
    if re.match(r"^\d+(\.\d+)?$", raw):
        sec = float(raw)
        if sec <= 0:
            raise ValueError("timeout must be positive")
        return sec
    total = 0.0
    pos = 0
    token = re.compile(r"(\d+(?:\.\d+)?)(ms|s|m|h)")
    for match in token.finditer(raw):
        if match.start() != pos:
            raise ValueError("invalid timeout: %s" % raw)
        num = float(match.group(1))
        unit = match.group(2)
        if unit == "ms":
            total += num / 1000.0
        elif unit == "s":
            total += num
        elif unit == "m":
            total += num * 60.0
        else:
            total += num * 3600.0
        pos = match.end()
    if pos != len(raw) or pos == 0:
        raise ValueError("invalid timeout: %s" % raw)
    if total <= 0:
        raise ValueError("timeout must be positive")
    return total


def args_error(args):
    """Validate flag combinations. Returns (message, hint), both None when the flags are usable."""
    has_left = _nonempty(args.left)
    has_right = _nonempty(args.right)
    has_admin = _nonempty(args.admin_endpoints)
    if not has_left and not has_right and not has_admin:
        return (
            "missing -l/--left, and no compare mode selected",
            "-l is the local file to check, then pick exactly one compare mode",
        )
    if not has_left:
        return "missing -l/--left (local probe YAML)", OPTION_HINTS["-l/--left"]
    if has_right and has_admin:
        return (
            "-r/--right and --admin-endpoints are mutually exclusive",
            "keep --admin-endpoints to compare against admin, or -r to compare two files",
        )
    if not has_right and not has_admin:
        return (
            "no compare mode selected",
            "add --admin-endpoints <host:port> for admin compare, or -r <file> for offline compare",
        )
    extra = (
        args.cloud_id is not None
        or _nonempty(args.local_ip)
        or _nonempty(args.local_ip_interface)
        or args.timeout is not None
    )
    if has_right and extra:
        return (
            "-r/--right cannot be used with --cloud-id, --local-ip, --local-ip-interface or --timeout",
            "those options only apply to --admin-endpoints mode, drop them for offline compare",
        )
    return None, None


def unlink_quiet(path):
    try:
        os.remove(path)
    except OSError:
        pass


def run_gen_config(bin_abs, install_root, args, timeout_sec):
    fd, tmp_path = tempfile.mkstemp(prefix="probe-gen-config-", suffix=".yaml")
    os.close(fd)
    lock_path = tmp_path + ".lock"
    timeout_str = args.timeout if _nonempty(args.timeout) else DEFAULT_GENCONFIG_TIMEOUT
    cloud_id = 0 if args.cloud_id is None else args.cloud_id
    argv = [
        bin_abs,
        "gen-config",
        "--admin-endpoints",
        to_text(args.admin_endpoints).strip(),
        "--cloud-id",
        str(cloud_id),
        "--timeout",
        timeout_str,
        "-o",
        tmp_path,
    ]
    if _nonempty(args.local_ip):
        argv.extend(["--local-ip", to_text(args.local_ip).strip()])
    elif _nonempty(args.local_ip_interface):
        argv.extend(["--local-ip-interface", to_text(args.local_ip_interface).strip()])
    wait_sec = timeout_sec + 2
    try:
        code, _out, err = run_cmd(argv, cwd=install_root, timeout=wait_sec)
        if code is None:
            return None, err or "gen-config failed"
        if code != 0:
            msg = err.strip() or "gen-config exited %s" % code
            return None, msg
        try:
            expected = load_mapping(tmp_path)
        except LoadError as load_err:
            return None, to_text(load_err)
        # The temp file starts out empty, so gen-config treats it as a first deployment and
        # writes an admin block built from the flags above rather than from the machine. Those
        # flags are this script's own defaults, not what the operator provisioned, so comparing
        # them against the live file would report bk_cloud_id or localIP as a difference on any
        # host that was set up with other values. The block is local state anyway, which is the
        # category the subset rule exists to ignore.
        if isinstance(expected, dict):
            expected.pop("admin", None)
        return expected, None
    finally:
        unlink_quiet(tmp_path)
        unlink_quiet(lock_path)


def resolve_install_root(left_path, bin_path):
    left_abs = os.path.abspath(left_path)
    unix_left = left_abs.replace("\\", "/")
    if unix_left.endswith("/etc/probe.yaml"):
        return os.path.dirname(os.path.dirname(left_abs))
    if bin_path:
        bin_abs = os.path.abspath(bin_path)
        parent = os.path.dirname(bin_abs)
        if os.path.basename(parent) == "bin":
            return os.path.dirname(parent)
    return os.getcwd()


def resolve_bin_path(install_root, bin_path):
    if bin_path:
        return os.path.abspath(bin_path)
    return os.path.abspath(os.path.join(install_root, "bin", "dbha-probe"))


def resolve_pid_file(left_cfg, install_root):
    pid_file = left_cfg.get("pidFile")
    if pid_file is None:
        return None
    text = to_text(pid_file)
    if os.path.isabs(text):
        return text
    return os.path.abspath(os.path.join(install_root, text))


def read_pid_file(path):
    if not path or not os.path.isfile(path):
        return None, "pid file not found: %s" % (path or "")
    try:
        handle = io.open(path, "r", encoding="utf-8-sig")
        try:
            raw = handle.read().strip()
        finally:
            handle.close()
    except (IOError, OSError) as err:
        return None, "cannot read pid file, errmsg: %s" % err
    if not raw or not raw.lstrip("-").isdigit():
        return None, "invalid pid file"
    pid = int(raw)
    if pid <= 0:
        return None, "invalid pid: %d" % pid
    return pid, None


def proc_alive(pid):
    return os.path.exists("/proc/%d" % pid)


def read_proc_cmdline(pid):
    path = "/proc/%d/cmdline" % pid
    try:
        handle = io.open(path, "rb")
        try:
            raw = handle.read()
        finally:
            handle.close()
    except (IOError, OSError):
        return u""
    parts = [p for p in raw.split(b"\x00") if p]
    decoded = []
    for part in parts:
        decoded.append(to_unicode(part))
    return u" ".join(decoded)


def read_proc_comm(pid):
    path = "/proc/%d/comm" % pid
    try:
        handle = io.open(path, "r", encoding="utf-8")
        try:
            return handle.read().strip()
        finally:
            handle.close()
    except (IOError, OSError, UnicodeDecodeError):
        return u""


def read_proc_ppid(pid):
    path = "/proc/%d/stat" % pid
    try:
        handle = io.open(path, "r", encoding="utf-8")
        try:
            data = handle.read()
        finally:
            handle.close()
    except (IOError, OSError, UnicodeDecodeError):
        return None
    close = data.rfind(")")
    if close < 0:
        return None
    fields = data[close + 1 :].split()
    if len(fields) < 2:
        return None
    try:
        return int(fields[1])
    except ValueError:
        return None


def read_proc_exe(pid):
    path = "/proc/%d/exe" % pid
    try:
        return os.readlink(path)
    except OSError:
        return u""


def exe_matches(exe_path, bin_abs, comm):
    if not exe_path:
        return False
    cleaned = exe_path.split(" (deleted)")[0]
    try:
        want = os.path.realpath(bin_abs)
    except OSError:
        want = os.path.abspath(bin_abs)
    try:
        got = os.path.realpath(cleaned)
    except OSError:
        got = cleaned
    if got == want or os.path.abspath(cleaned) == os.path.abspath(bin_abs):
        return True
    if " (deleted)" in exe_path:
        return comm == os.path.basename(bin_abs)
    return False


def classify_cmdline(cmdline):
    tokens = cmdline.split()
    for tok in tokens:
        if tok in ("ensure", "ensure-keepalive"):
            return KIND_SKIP
    if "--ping-http-addr" in cmdline:
        return KIND_SKIP
    for tok in tokens:
        if tok == "daemon-start":
            return KIND_GUARD
    return KIND_WORKER


def list_probe_procs(bin_abs):
    procs = []
    if not os.path.isdir("/proc"):
        return None, "need /proc to inspect probe processes"
    try:
        names = os.listdir("/proc")
    except OSError as err:
        return None, "cannot list /proc, errmsg: %s" % err
    want_comm = os.path.basename(bin_abs)
    for name in names:
        if not name.isdigit():
            continue
        pid = int(name)
        comm = read_proc_comm(pid)
        exe = read_proc_exe(pid)
        if not exe_matches(exe, bin_abs, comm):
            continue
        cmdline = read_proc_cmdline(pid)
        kind = classify_cmdline(cmdline)
        if kind == KIND_SKIP:
            continue
        ppid = read_proc_ppid(pid)
        procs.append({"pid": pid, "kind": kind, "ppid": ppid, "cmdline": cmdline})
    return procs, None


def check_health(bin_abs, left_abs, install_root):
    result = {"ok": False, "fatal": False, "fields": [], "pid": None}
    if not os.path.isfile(bin_abs):
        result["fatal"] = True
        result["fields"] = [("errmsg", "probe binary not found: %s" % bin_abs)]
        return result
    if not os.access(bin_abs, os.X_OK):
        result["fatal"] = True
        result["fields"] = [("errmsg", "probe binary not executable: %s" % bin_abs)]
        return result
    code, out, err = run_cmd(
        [bin_abs, "health", "-j", "-c", left_abs],
        cwd=install_root,
        timeout=HEALTH_TIMEOUT_SEC,
    )
    if code is None:
        result["fatal"] = True
        msg = err or "health command failed"
        result["fields"] = [("errmsg", msg)]
        return result
    text = out.strip().splitlines()
    if not text:
        result["fatal"] = True
        result["fields"] = [("errmsg", "health produced no json")]
        return result
    try:
        payload = json.loads(text[-1])
    except ValueError:
        result["fatal"] = True
        result["fields"] = [("errmsg", "health stdout is not json")]
        return result
    if not isinstance(payload, dict):
        result["fatal"] = True
        result["fields"] = [("errmsg", "health json must be an object")]
        return result
    status = to_unicode(payload.get("status", ""))
    pid = payload.get("pid")
    proc_name = payload.get("procName") or payload.get("proc_name") or ""
    errmsg = payload.get("errmsg") or ""
    db_types = payload.get("db_types") or payload.get("dbTypes") or []
    result["pid"] = pid
    result["fields"] = [
        ("status", status or "unknown"),
        ("pid", "%s" % pid),
        ("proc", to_unicode(proc_name)),
    ]
    if errmsg:
        result["fields"].append(("errmsg", to_unicode(errmsg)))
    if db_types:
        if isinstance(db_types, list):
            shown = ", ".join([to_unicode(x) for x in db_types])
        else:
            shown = to_unicode(db_types)
        result["fields"].append(("db_types", shown))
    if status == "running" and pid not in (None, -1, "-1"):
        result["ok"] = True
    return result


def check_guard(left_cfg, install_root, bin_abs, health_pid):
    result = {"ok": False, "fatal": False, "fields": []}
    if not os.path.isdir("/proc"):
        result["fields"] = [("errmsg", "need /proc to inspect probe processes")]
        return result
    pid_path = resolve_pid_file(left_cfg, install_root)
    file_pid, pid_err = read_pid_file(pid_path)
    if pid_err:
        result["fields"] = [("errmsg", pid_err)]
        return result
    if not proc_alive(file_pid):
        result["fields"] = [
            ("errmsg", "pid file process not running, pid: %d" % file_pid),
        ]
        return result
    cmdline = read_proc_cmdline(file_pid)
    kind = classify_cmdline(cmdline)
    if kind != KIND_GUARD:
        result["fields"] = [
            ("pid", "%d" % file_pid),
            ("errmsg", "pid file is not a daemon-start guard"),
        ]
        return result
    procs, scan_err = list_probe_procs(bin_abs)
    if scan_err:
        result["fields"] = [("errmsg", scan_err)]
        return result
    guards = [p for p in procs if p["kind"] == KIND_GUARD]
    workers = [p for p in procs if p["kind"] == KIND_WORKER]
    if len(guards) != 1 or guards[0]["pid"] != file_pid:
        result["fields"] = [
            ("pid", "%d" % file_pid),
            ("errmsg", "expected one daemon-start guard matching pid file"),
        ]
        return result
    children = [p for p in workers if p["ppid"] == file_pid]
    orphans = [p for p in workers if p["ppid"] != file_pid]
    if orphans:
        result["fields"] = [
            ("guard_pid", "%d" % file_pid),
            ("errmsg", "orphan worker pid: %d" % orphans[0]["pid"]),
        ]
        return result
    if len(children) != 1:
        result["fields"] = [
            ("guard_pid", "%d" % file_pid),
            ("errmsg", "expected one worker child of guard, got %d" % len(children)),
        ]
        return result
    if health_pid not in (None, -1, "-1") and int(health_pid) != file_pid:
        result["fields"] = [
            ("guard_pid", "%d" % file_pid),
            ("health_pid", "%s" % health_pid),
            ("errmsg", "health pid does not match pid file"),
        ]
        return result
    result["ok"] = True
    result["fields"] = [
        ("guard_pid", "%d" % file_pid),
        ("worker_pid", "%d" % children[0]["pid"]),
    ]
    return result


def _extract_cd_path(line):
    match = re.search(r"\bcd\s+(\"[^\"]*\"|'[^']*'|\S+)", line)
    if not match:
        return None
    raw = match.group(1)
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("\"", "'"):
        return raw[1:-1]
    return raw


def _cron_c_ok(line):
    return bool(re.search(r"(?:^|\s)-c\s+(?:\./)?etc/probe\.yaml(?:\s|$)", line))


def _cron_cmd_ok(line):
    """Accept ensure (current start-probe register) or ./start-probe.sh --from-cron."""
    if "./start-probe.sh" in line and "--from-cron" in line:
        return True
    if "./bin/dbha-probe ensure" in line and "--from-cron" in line and _cron_c_ok(line):
        return True
    return False


def check_cron_text(text, install_root):
    """Validate crontab listing text. Does not run crontab. Returns (ok, fields)."""
    lines = []
    for raw in to_unicode(text).splitlines():
        if CRON_MARKER in raw:
            lines.append(raw)
    if not lines:
        return False, [("errmsg", "missing crontab marker: %s" % CRON_MARKER)]
    if len(lines) != 1:
        msg = "expected one %s line, got %d" % (CRON_MARKER, len(lines))
        return False, [("errmsg", msg)]
    line = lines[0].strip()
    fields = [("marker", CRON_MARKER)]
    if not re.match(r"^\*\s+\*\s+\*\s+\*\s+\*\s+", line):
        return False, fields + [("errmsg", "schedule must be * * * * *")]
    cd_path = _extract_cd_path(line)
    if not cd_path:
        return False, fields + [("errmsg", "missing cd to install root")]
    try:
        want = os.path.realpath(install_root)
        got = os.path.realpath(cd_path)
    except OSError:
        want = os.path.abspath(install_root)
        got = os.path.abspath(cd_path)
    if got != want:
        return False, fields + [("errmsg", "cd path is not install root")]
    if "--from-cron" not in line:
        return False, fields + [("errmsg", "missing --from-cron")]
    if not _cron_cmd_ok(line):
        return False, fields + [
            ("errmsg", "need ./start-probe.sh --from-cron or ./bin/dbha-probe ensure"),
        ]
    if CRON_LOG_NAME not in line:
        return False, fields + [("errmsg", "need log file %s" % CRON_LOG_NAME)]
    return True, fields


def check_cron(install_root):
    result = {"ok": False, "fatal": False, "fields": []}
    argv = ["crontab", "-l"]
    code, out, err = run_cmd(argv, cwd=None, timeout=HEALTH_TIMEOUT_SEC)
    if code is None and err.startswith("command not found"):
        result["fatal"] = True
        result["fields"] = [("errmsg", err)]
        return result
    if code is None:
        result["fatal"] = True
        result["fields"] = [("errmsg", err or "crontab -l failed")]
        return result
    if code != 0:
        err_l = err.lower()
        if "no crontab" in err_l or out.strip() == "":
            result["fields"] = [("errmsg", "no crontab for this user")]
            return result
        result["fields"] = [("errmsg", err.strip() or "crontab -l failed")]
        return result
    ok, fields = check_cron_text(out, install_root)
    result["ok"] = ok
    result["fields"] = fields
    return result


def render_check(title, ok_label, fail_label, result):
    status = "PASS" if result["ok"] else "FAIL"
    label = ok_label if result["ok"] else fail_label
    marker = paint("[%s]" % status, ANSI_BOLD + status_style(status))
    lines = ["%s %-7s %s" % (marker, title.upper(), label)]
    for key, value in result["fields"]:
        field_style = ANSI_RED if key == "errmsg" and not result["ok"] else ANSI_CYAN
        lines.append(render_field(key, value, 10, field_style))
    return lines


class ReportArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        text, hint = friendly_arg_error(message)
        emit_early_error(text, hint=hint, usage=True)
        self.exit(EXIT_ERROR)


def build_parser():
    parser = ReportArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="%(prog)s " + USAGE_ADMIN_ARGS + "\n       %(prog)s " + USAGE_OFFLINE_ARGS,
        description=(
            "Compare a local probe YAML with another file or with gen-config from admin,\n"
            "then check probe runtime health."
        ),
        epilog="examples:\n" + "\n".join("  " + line for line in example_lines()),
    )
    parser.add_argument(
        "-l",
        "--left",
        default=None,
        help="local YAML file (required)",
    )
    parser.add_argument(
        "-r",
        "--right",
        default=None,
        help="offline YAML file (mutually exclusive with --admin-endpoints)",
    )
    parser.add_argument(
        "--admin-endpoints",
        default=None,
        help="admin host:port, separated by ; (mutually exclusive with -r/--right)",
    )
    parser.add_argument(
        "--cloud-id",
        default=None,
        type=parse_cloud_id,
        help="bk_cloud_id for gen-config (default: 0)",
    )
    parser.add_argument(
        "--local-ip",
        default=None,
        help="probe local IP for gen-config",
    )
    parser.add_argument(
        "--local-ip-interface",
        default=None,
        help="interface name when auto-detecting --local-ip",
    )
    parser.add_argument(
        "--timeout",
        default=None,
        help="gen-config timeout (default: %s)" % DEFAULT_GENCONFIG_TIMEOUT,
    )
    parser.add_argument(
        "-b",
        "--bin",
        default=None,
        help="probe binary (default: <install-root>/bin/dbha-probe)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable ANSI colors",
    )
    return parser


def emit_runtime(health, guard, cron):
    emit(section_header("RUNTIME CHECKS"))
    for line in render_check("health", "healthy", "unhealthy", health):
        emit(line)
    for line in render_check("guard", "ok", "fail", guard):
        emit(line)
    for line in render_check("cron", "ok", "fail", cron):
        emit(line)


def emit_config_result(diffs, left_label, right_label, labels, error=None):
    for line in render_config_report(diffs, left_label, right_label, labels, error):
        emit(line)


def runtime_passed(health, guard, cron):
    return sum(1 for result in (health, guard, cron) if result["ok"])


def emit_final_result(exit_code, diff_count, health=None, guard=None, cron=None, config_error=False):
    status = {
        EXIT_EQUAL: "PASSED",
        EXIT_DIFF: "FAILED",
        EXIT_ERROR: "ERROR",
    }[exit_code]
    emit("")
    emit(section_header("RESULT", status))
    config_text = "error" if config_error else (
        "passed" if diff_count == 0 else "%d difference(s)" % diff_count
    )
    if health is None or guard is None or cron is None:
        runtime_text = "not run"
    else:
        runtime_text = "%d/3 passed" % runtime_passed(health, guard, cron)
    emit(
        "Config: %s | Runtime: %s | Exit code: %d"
        % (config_text, runtime_text, exit_code)
    )


def script_name():
    name = os.path.basename(sys.argv[0] or "")
    return name or "compare_probe_config.py"


def usage_lines():
    name = script_name()
    return ["%s %s" % (name, USAGE_ADMIN_ARGS), "%s %s" % (name, USAGE_OFFLINE_ARGS)]


def example_lines():
    name = script_name()
    return ["./%s %s" % (name, EXAMPLE_ADMIN_ARGS), "./%s %s" % (name, EXAMPLE_OFFLINE_ARGS)]


def render_field_block(label, values, width, style=None):
    """Render one field whose value spans several lines, keeping continuations aligned."""
    lines = []
    for index, text in enumerate(values):
        if index == 0:
            lines.append(render_field(label, text, width, style))
        else:
            lines.append("    %s %s" % (" " * width, text))
    return lines


_REQUIRED_ARGS_RE = re.compile(r"^the following arguments are required:\s*(.+)$")
_UNRECOGNIZED_ARGS_RE = re.compile(r"^unrecognized arguments:\s*(.+)$")
_ARGUMENT_RE = re.compile(r"^argument ([^:]+):\s*(.+)$")
_EXPECTED_ARG_RE = re.compile(r"^argument ([^:]+): expected one argument$")


def friendly_arg_error(message):
    """Turn argparse wording into an actionable message. Returns (message, hint)."""
    text = to_text(message).strip()
    match = _EXPECTED_ARG_RE.match(text)
    if match:
        flags = match.group(1)
        return "%s needs a value" % flags, OPTION_HINTS.get(flags, HINT_SEE_HELP)
    match = _REQUIRED_ARGS_RE.match(text)
    if match:
        flags = match.group(1)
        return "missing required option %s" % flags, OPTION_HINTS.get(flags, HINT_SEE_HELP)
    match = _UNRECOGNIZED_ARGS_RE.match(text)
    if match:
        return "unknown option: %s" % match.group(1), HINT_SEE_HELP
    match = _ARGUMENT_RE.match(text)
    if match:
        flags = match.group(1)
        return "%s: %s" % (flags, match.group(2)), OPTION_HINTS.get(flags, HINT_SEE_HELP)
    return text, None


def load_error_hint(message, flag="-l"):
    """Suggest a fix for a YAML read or parse failure on the file given to flag."""
    text = to_text(message)
    if "file not found" in text or "is a directory" in text:
        if flag == "-l":
            return "run this from the probe install root, where the config is usually etc/probe.yaml"
        return "%s must point to an existing YAML file" % flag
    if "yaml parse failed" in text:
        return "fix that line: indent with spaces only and keep a space after each 'key:'"
    if "empty yaml" in text or "multiple yaml documents" in text:
        return "the file must hold exactly one non-empty YAML mapping"
    if "decode failed" in text:
        return "the file must be UTF-8 encoded"
    return None


def emit_early_error(message, path=None, hint=None, usage=False, path_label="Local"):
    width = ERROR_FIELD_WIDTH
    emit(section_header("PROBE CONFIG CHECK", "ERROR"), sys.stderr)
    if path:
        emit(render_field(path_label, path, width, ANSI_CYAN), sys.stderr)
    emit(render_field("Error", message, width, ANSI_RED), sys.stderr)
    if hint:
        emit(render_field("Hint", hint, width, ANSI_YELLOW), sys.stderr)
    if usage:
        for line in render_field_block("Usage", usage_lines(), width, ANSI_CYAN):
            emit(line, sys.stderr)
        emit(render_field("Example", example_lines()[0], width, ANSI_CYAN), sys.stderr)
    emit("", sys.stderr)
    emit(section_header("RESULT", "ERROR"), sys.stderr)
    emit("Config: error | Runtime: not run | Exit code: 2", sys.stderr)


def main(argv=None):
    raw_argv = sys.argv[1:] if argv is None else argv
    configure_color("--no-color" in raw_argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_color(args.no_color)
    err, hint = args_error(args)
    if err:
        emit_early_error(err, args.left, hint=hint, usage=True)
        return EXIT_ERROR

    try:
        local_cfg = load_mapping(args.left)
    except LoadError as load_err:
        message = to_text(load_err)
        emit_early_error(message, args.left, hint=load_error_hint(message))
        return EXIT_ERROR

    left_abs = os.path.abspath(args.left)
    install_root = resolve_install_root(args.left, args.bin)
    bin_abs = resolve_bin_path(install_root, args.bin)

    diffs = []
    yaml_fatal = False
    use_admin = _nonempty(args.admin_endpoints)
    if use_admin:
        timeout_str = args.timeout if _nonempty(args.timeout) else DEFAULT_GENCONFIG_TIMEOUT
        try:
            timeout_sec = parse_timeout_sec(timeout_str)
        except ValueError as timeout_err:
            emit_early_error(to_text(timeout_err), args.left, hint=OPTION_HINTS["--timeout"])
            return EXIT_ERROR
        expected, gen_err = run_gen_config(bin_abs, install_root, args, timeout_sec)
        if gen_err:
            emit_config_result([], GENCONFIG_LABEL, args.left, LABELS_ADMIN, gen_err)
            yaml_fatal = True
        else:
            walk("", expected, local_cfg, diffs, ignore_extra_right=True)
            emit_config_result(diffs, GENCONFIG_LABEL, args.left, LABELS_ADMIN)
    else:
        try:
            right_cfg = load_mapping(args.right)
        except LoadError as load_err:
            message = to_text(load_err)
            emit_early_error(
                message,
                args.right,
                hint=load_error_hint(message, "-r"),
                path_label="Right",
            )
            return EXIT_ERROR
        walk("", local_cfg, right_cfg, diffs)
        emit_config_result(diffs, args.left, args.right, LABELS_OFFLINE)

    health = check_health(bin_abs, left_abs, install_root)
    guard = check_guard(local_cfg, install_root, bin_abs, health.get("pid"))
    cron = check_cron(install_root)
    emit("")
    emit_runtime(health, guard, cron)

    if yaml_fatal or health.get("fatal") or guard.get("fatal") or cron.get("fatal"):
        exit_code = EXIT_ERROR
    elif diffs or runtime_passed(health, guard, cron) != 3:
        exit_code = EXIT_DIFF
    else:
        exit_code = EXIT_EQUAL
    emit_final_result(exit_code, len(diffs), health, guard, cron, yaml_fatal)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
