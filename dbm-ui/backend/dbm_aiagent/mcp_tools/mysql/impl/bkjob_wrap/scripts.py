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
# 各 bkjob 功能的 inline 脚本（一个功能一个脚本，定义在 impl 层，避免耦合视图）

# 获取目标机器当前日期和 IP
CURRENT_DATE_AND_IP_SCRIPT = """echo $LOCAL_IP && date"""

# 磁盘目录大小统计：分区总览 / 一级子目录 / 关键目录深扫 / 大文件（>20G）
DISK_DIR_SIZE_SCRIPT = """#!/bin/sh
# ============================================================
# Disk Usage Statistics Script (POSIX sh compatible)
# Purpose:
#   1. Show disk partition usage (df: total/used/available)
#   2. For each partition (mount point) from df, show first-level subdirectory sizes
#   3. Key directories deep scan:
#      - /home/mysql/*
#      - /data/home/*
#      - mysqllog/*/*   (under each partition)
#      - mysqldata/*/*/* (under each partition)
#   4. Files larger than 20G under the key directories
#      (mysqldata/mysqllog are scanned ONCE via du -a, reused by Part 2/3)
# Usage: sh disk_usage.sh [dir1] [dir2] ...
# Example: sh disk_usage.sh / /data
# ============================================================

# Re-run self with a hard timeout and lowered IO/CPU priority (if possible),
# so the scan never blocks for long and does not compete with the database.
# Override the timeout with DISK_USAGE_TIMEOUT (default: 60 seconds).
TIMEOUT_SECS="${DISK_USAGE_TIMEOUT:-60}"
if [ -z "$DISK_USAGE_RENICED" ]; then
    export DISK_USAGE_RENICED=1
    # timeout prefix (kills the whole process group after the limit)
    TP=""
    if command -v timeout >/dev/null 2>&1; then
        TP="timeout -k 2 $TIMEOUT_SECS"
    fi
    if command -v ionice >/dev/null 2>&1; then
        $TP ionice -c3 nice -n 19 "$0" "$@"
    elif command -v nice >/dev/null 2>&1; then
        $TP nice -n 19 "$0" "$@"
    else
        $TP "$0" "$@"
    fi
    status=$?
    # timeout 超时退出码为 124（被 -k 强杀时为 137），输出明确标记避免结果被误当作完整数据
    if [ "$status" = "124" ] || [ "$status" = "137" ]; then
        echo "[TRUNCATED] scan hit timeout after ${TIMEOUT_SECS}s, results may be incomplete" >&2
    fi
    exit "$status"
fi

# Output result to /home/mysql/disk_usage_<YYYYMMDD_HHMMSS> AND show on screen
OUT_DIR="/home/mysql"
if [ ! -d "$OUT_DIR" ]; then
    echo "[WARNING] $OUT_DIR does not exist, saving to current directory"
    OUT_DIR="."
fi
OUT_FILE="$OUT_DIR/disk_usage_$(date '+%Y%m%d_%H%M%S')"
exec 3>&1                    # keep original stdout (fd 3) for screen display
echo "[Output] saving results to: $OUT_FILE" >&3
exec > "$OUT_FILE" 2>&1      # all output -> file
# 超时被强杀前在结果文件中留下明确标记，避免结果被误当作完整数据
trap 'echo "[TRUNCATED] scan hit timeout, results may be incomplete" >> "$OUT_FILE"' TERM

# Partitions to scan; can be overridden by command-line arguments.
# Default: all mount points from df (pseudo file systems excluded)
if [ $# -gt 0 ]; then
    DIRS="$*"
else
    DIRS=""
    for mount in $(df -P 2>/dev/null | tail -n +2 | awk '{print $NF}'); do
        case "$mount" in
            /dev|/dev/*|/proc|/proc/*|/sys|/sys/*|/run|/run/*|/tmp) continue ;;
        esac
        DIRS="$DIRS $mount"
    done
    [ -z "$DIRS" ] && DIRS="/"
fi

# Virtual file systems (scanning them is slow and meaningless), excluded from du
VFS_DIRS="proc sys dev run tmp"

TS=$(date '+%Y-%m-%d %H:%M:%S')
echo "============================================================"
echo "Disk Usage Statistics   Time: $TS"
echo "Partitions: $DIRS"
echo "============================================================"

# ============ Disk Partition Overview (all mounted filesystems) ============
echo "[Disk Partition Overview - Total / Used / Available / Use%]"
df -h 2>/dev/null | sed 's/^/  /'
echo "============================================================"

# ============ Part 1: per-partition first-level directory sizes ============
for dir in $DIRS; do
    echo
    echo "------------------ $dir ------------------"

    if [ ! -d "$dir" ]; then
        echo "[WARNING] Directory does not exist, skipped: $dir"
        continue
    fi

    # Real device (disk) of the mount point, resolved from df / findmnt
    dev=$(findmnt -no SOURCE "$dir" 2>/dev/null || df -P "$dir" 2>/dev/null | tail -n +2 | awk '{print $1}')
    echo "[Real Device] $dir -> ${dev:-unknown}"

    # Build arguments to exclude virtual file systems
    EXCL=""
    for v in $VFS_DIRS; do
        [ -d "$dir/$v" ] && EXCL="$EXCL --exclude=$dir/$v"
    done
    # NOTE: mysqldata/mysqllog are intentionally KEPT in the partition scan so
    # the first-level listing is complete (full directory sizes). They are
    # scanned once more in Part 2/3 for deep statistics.

    # Show disk partition usage (total/used/available) for the mounted filesystem of this directory
    echo "[Disk Partition: $dir]"
    df -h "$dir" 2>/dev/null | sed 's/^/  /'

    echo "[Total Size] and [First-level subdirectories, sorted by size (largest first)]"
    if [ "$dir" = "/" ]; then
        # Root: only show total size of /tmp
        if [ -d /tmp ]; then
            echo "[Total Size] /tmp"
            du -sh /tmp 2>/dev/null
        fi
    else
        # One-pass scan (max-depth=1): partition total size + full size of
        # every first-level subdirectory, avoiding two full traversals.
        # shellcheck disable=SC2086
        du -h --max-depth=1 $EXCL "$dir" 2>/dev/null | sort -rh -S 512M 2>/dev/null | head -n 30
    fi
    echo
done

# ============ mysqldata / mysqllog du -a cache (single traversal) ============
# One full scan per key data dir; cached results are reused by Part 2
# (dir sizes) and Part 3 (files > 20G) - no re-traversal.
# Row types: T=total(dir itself), D=dir, F=file>20G
MYSQLDATA_CACHE="/tmp/mysqldata_du_cache_$$.txt"
trap 'rm -f "$MYSQLDATA_CACHE"' EXIT INT TERM
:: > "$MYSQLDATA_CACHE"
for dir in $DIRS; do
    for sub in mysqldata mysqllog; do
        if [ -d "$dir/$sub" ]; then
            if [ "$sub" = "mysqllog" ]; then maxd=2; exact=0; else maxd=3; exact=1; fi
            du -a "$dir/$sub" 2>/dev/null | awk -F'\\t' -v m="$dir/$sub" -v maxd="$maxd" -v exact="$exact" -v cutoff=20971520 '
                function dep(p, n, a, c, i) { n=split(p,a,"/"); c=0; for(i=1;i<=n;i++) if(a[i]!="") c++; return c }
                {
                  sz=$1+0; p=$2;
                  # GNU du outputs children before parents, so when we see p,
                  # its children (if any) have already been emitted and marked
                  # p as a directory. Mark every ancestor of p as a dir here.
                  # This keeps memory at O(number of dirs), not O(all entries).
                  q=p;
                  while (q != "/" && q != "") {
                    sub(/\\/[^/]*$/, "", q);
                    if (q == "" || q == "/") break;
                    dirs[q]=1;
                  }
                  d = dep(p) - dep(m);
                  if (dirs[p] == 1) {
                    if (d==0) printf "T\\t%d\\t%s\\n", sz, p;
                    else if (d>0 && (exact ? d==maxd : d<=maxd)) printf "D\\t%d\\t%s\\n", sz, p;
                  } else if (sz>cutoff) {
                    printf "F\\t%d\\t%s\\n", sz, p;
                  }
                }' >> "$MYSQLDATA_CACHE"
        fi
    done
done

# ============ Part 2: key directories deep scan ============
echo
echo "============================================================"
echo "Key Directories Deep Scan"
echo "============================================================"

# Absolute key directories
# /home/mysql: only total size
if [ -d /home/mysql ]; then
    echo "[Key Dir: /home/mysql]"
    du -sh /home/mysql 2>/dev/null
    echo
fi

# /data/home: total size + first-level subdirectories
if [ -d /data/home ]; then
    echo "[Key Dir: /data/home]"
    du -sh /data/home 2>/dev/null
    echo "[Key Dir: /data/home/*]"
    du -sh /data/home/* 2>/dev/null | sort -rh -S 512M 2>/dev/null | head -n 30
    echo
fi

# Relative key directories under each partition
for dir in $DIRS; do
    if [ -d "$dir/mysqllog" ]; then
        echo "[Key Dir: $dir/mysqllog]"
        awk -F'\\t' -v m="$dir/mysqllog" '$1=="T" && $3==m {printf "%.1fG\\t%s\\n", $2/1024/1024, $3}' "$MYSQLDATA_CACHE"
        echo "[Key Dir: $dir/mysqllog subdirs]"
        awk -F'\\t' -v m="$dir/mysqllog" '
            $1=="D" && index($3, m"/")==1 {printf "%.1fG\\t%s\\n", $2/1024/1024, $3}
        ' "$MYSQLDATA_CACHE" \\
            | sort -rn -S 512M 2>/dev/null | head -n 30
        echo
    fi
    if [ -d "$dir/mysqldata" ]; then
        echo "[Key Dir: $dir/mysqldata]"
        awk -F'\\t' -v m="$dir/mysqldata" '$1=="T" && $3==m {printf "%.1fG\\t%s\\n", $2/1024/1024, $3}' "$MYSQLDATA_CACHE"
        echo "[Key Dir: $dir/mysqldata/*/*/*]"
        awk -F'\\t' -v m="$dir/mysqldata" '
            $1=="D" && index($3, m"/")==1 {printf "%.1fG\\t%s\\n", $2/1024/1024, $3}
        ' "$MYSQLDATA_CACHE" \\
            | sort -rn -S 512M 2>/dev/null | head -n 30
        echo
    fi
done

# ============ Part 3: files larger than 20G under key directories ============
echo
echo "============================================================"
echo "Files Larger Than 20G Under Key Directories"
echo "============================================================"

# Show files larger than 20G under the given directory (GNU find required)
show_large_files() {
    key="$1"
    [ -d "$key" ] || return 0
    echo "[Files > 20G under $key]"
    find "$key" -maxdepth 8 -type f -size +20G -printf '%s\\t%p\\n' 2>/dev/null \\
        | sort -rn -S 512M 2>/dev/null \\
        | awk '{printf "%.1fG\\t%s\\n", $1/1073741824, $2}' 2>/dev/null \\
        | head -n 30
}

# Absolute key directories
for key in /home/mysql /data/home; do
    [ -d "$key" ] && show_large_files "$key"
done

# Relative key directories under each partition
# mysqllog/mysqldata: large files come from the du -a cache (no re-traversal)
for dir in $DIRS; do
    if [ -d "$dir/mysqllog" ]; then
        echo "[Files > 20G under $dir/mysqllog]"
        awk -F'\\t' -v m="$dir/mysqllog" '
            $1=="F" && index($3, m"/")==1 {printf "%.1fG\\t%s\\n", $2/1024/1024, $3}
        ' "$MYSQLDATA_CACHE" \\
            | sort -rn -S 512M 2>/dev/null | head -n 30
    fi
    if [ -d "$dir/mysqldata" ]; then
        echo "[Files > 20G under $dir/mysqldata]"
        awk -F'\\t' -v m="$dir/mysqldata" '
            $1=="F" && index($3, m"/")==1 {printf "%.1fG\\t%s\\n", $2/1024/1024, $3}
        ' "$MYSQLDATA_CACHE" \\
            | sort -rn -S 512M 2>/dev/null | head -n 30
    fi
done

echo "============================================================"
echo "Statistics completed"
echo "============================================================"

# restore original stdout and show the saved result on screen
exec >&3 3>&-
cat "$OUT_FILE"
"""
