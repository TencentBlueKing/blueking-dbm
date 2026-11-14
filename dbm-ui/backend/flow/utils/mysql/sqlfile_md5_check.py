# -*- coding: utf-8 -*-
import re
import shlex
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from backend.ticket.constants import TicketType

MD5_LINE_PREFIX = "DBM_SQLFILE_MD5_V1"
MISSING_DIGEST = "MISSING"

_SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MD5_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_FORCE_TICKET_TYPES = {
    TicketType.MYSQL_FORCE_IMPORT_SQLFILE.value,
    TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE.value,
}


@dataclass(frozen=True)
class Skip:
    reason: str


@dataclass(frozen=True)
class Proceed:
    sql_files_md5: dict


@dataclass(frozen=True)
class ParseFailure:
    raw_lines: Tuple[str, ...]


@dataclass(frozen=True)
class Md5Failure:
    filename: str
    kind: str
    expected: Optional[str] = None
    actual: Optional[str] = None


def decide_md5_check(sql_files_md5, ticket_type) -> Union[Skip, Proceed]:
    if ticket_type in _FORCE_TICKET_TYPES:
        return Skip(reason="force")
    if sql_files_md5 is None:
        return Skip(reason="missing")
    if not isinstance(sql_files_md5, dict) or not sql_files_md5:
        return Skip(reason="empty")
    return Proceed(sql_files_md5=sql_files_md5)


def parse_safe_filename(raw) -> Optional[str]:
    if not isinstance(raw, str) or ".." in raw:
        return None
    return raw if _SAFE_FILENAME_RE.fullmatch(raw) else None


def parse_md5_hex(raw) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    digest = raw.strip()
    return digest.lower() if _MD5_RE.fullmatch(digest) else None


def build_md5sum_script(sql_path: str, filenames: List[str]) -> str:
    lines = []
    for filename in filenames:
        path = shlex.quote("{}/{}".format(sql_path.rstrip("/"), filename))
        quoted_filename = shlex.quote(filename)
        lines.extend(
            [
                "if [ -f {path} ]; then".format(path=path),
                "  digest=$(md5sum -- {path} | awk '{{print $1}}')".format(path=path),
                "  printf 'DBM_SQLFILE_MD5_V1\\t%s\\t%s\\n' {filename} \"$digest\"".format(filename=quoted_filename),
                "else",
                "  printf 'DBM_SQLFILE_MD5_V1\\t%s\\tMISSING\\n' {filename}".format(filename=quoted_filename),
                "fi",
            ]
        )
    lines.append("exit 0")
    return "\n".join(lines)


def parse_md5_lines(log_content: str) -> Union[Dict[str, str], ParseFailure]:
    actual = {}
    malformed_lines = []
    saw_version_line = False
    for raw_line in (log_content or "").splitlines():
        if not raw_line.startswith(MD5_LINE_PREFIX):
            continue
        saw_version_line = True
        parts = raw_line.split("\t")
        if len(parts) != 3:
            malformed_lines.append(raw_line)
            continue
        prefix, filename, raw_digest = parts
        digest = parse_md5_hex(raw_digest)
        if (
            prefix != MD5_LINE_PREFIX
            or parse_safe_filename(filename) is None
            or (raw_digest != MISSING_DIGEST and digest is None)
            or filename in actual
        ):
            malformed_lines.append(raw_line)
            continue
        actual[filename] = MISSING_DIGEST if raw_digest == MISSING_DIGEST else digest
    if malformed_lines:
        return ParseFailure(raw_lines=tuple(malformed_lines))
    if not saw_version_line:
        raw = (log_content or "").strip()
        return ParseFailure(raw_lines=(raw[:500],) if raw else ("",))
    return actual


def compare_sqlfile_md5(expected: Dict[str, str], actual: Dict[str, str]) -> List[Md5Failure]:
    failures = []
    for filename, expected_digest in expected.items():
        normalized_expected = expected_digest.lower()
        actual_digest = actual.get(filename)
        if actual_digest is None or actual_digest == MISSING_DIGEST:
            failures.append(Md5Failure(filename=filename, kind="missing_file", expected=normalized_expected))
            continue
        normalized_actual = actual_digest.lower()
        if normalized_expected != normalized_actual:
            failures.append(
                Md5Failure(
                    filename=filename,
                    kind="mismatch",
                    expected=normalized_expected,
                    actual=normalized_actual,
                )
            )
    return failures
