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
import json
import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from backend.db_report.sqlserver_backup.backup_file_repair import repair_by_cluster, repair_one

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = _(
        "Repair missing SQLServer backup records (SQLServerBackupResult / SQLServerBinlogResult) "
        "based on remote BACKUP_TRACE + msdb.backupset.\n"
        "Usage examples:\n"
        "  # 单条 backup_id 试运行\n"
        "  python manage.py sqlserver_repair_backup_info --cluster_id 123 --backup_id xxx --backup_type log --dry-run\n"
        "  # 单条真实写入\n"
        "  python manage.py sqlserver_repair_backup_info --cluster_id 123 --backup_id xxx --backup_type log\n"
        "  # 集群最近 1 天全部 backup_id 扫描\n"
        "  python manage.py sqlserver_repair_backup_info --cluster_id 123 --backup_type log --since-days 1 --dry-run\n"
    )

    def add_arguments(self, parser):
        parser.add_argument("--cluster_id", type=int, required=True, help=_("集群 id"))
        parser.add_argument(
            "--backup_type",
            type=str,
            required=True,
            choices=["full", "log"],
            help=_("备份类型：full / log"),
        )
        parser.add_argument(
            "--backup_id",
            type=str,
            default="",
            help=_("指定单个 backup_id；不指定时按 --since-days 扫描整个集群"),
        )
        parser.add_argument(
            "--since-days",
            type=int,
            default=1,
            help=_("批量模式下扫描最近 N 天的 backup_id（仅在未指定 --backup_id 时生效），默认 1"),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help=_("试运行，只诊断不写库"),
        )

    def handle(self, *args, **options):
        cluster_id = options["cluster_id"]
        backup_type = options["backup_type"]
        backup_id = options["backup_id"]
        since_days = options["since_days"]
        dry_run = options["dry_run"]

        if backup_id:
            self.stdout.write(
                self.style.WARNING(
                    f"[repair][single] cluster_id={cluster_id} backup_id={backup_id} "
                    f"type={backup_type} dry_run={dry_run}"
                )
            )
            try:
                case, info = repair_one(cluster_id, backup_id, backup_type, dry_run=dry_run)
            except Exception as err:
                raise CommandError(f"repair failed: {err}")
            self._print_result(backup_id, case, info)
            return

        # 批量模式
        self.stdout.write(
            self.style.WARNING(
                f"[repair][batch] cluster_id={cluster_id} type={backup_type} "
                f"since_days={since_days} dry_run={dry_run}"
            )
        )
        results = repair_by_cluster(cluster_id, backup_type, dry_run=dry_run, since_days=since_days)
        if not results:
            self.stdout.write(self.style.SUCCESS("no backup_id found in time range"))
            return

        # 汇总
        summary = {}
        for backup_id_, case, info in results:
            self._print_result(backup_id_, case, info)
            summary[case] = summary.get(case, 0) + 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"[summary] total={len(results)} {summary}"))

    def _print_result(self, backup_id: str, case: str, info: dict):
        line = f"[{case}] backup_id={backup_id} | {json.dumps(info, ensure_ascii=False, default=str)}"
        if case == "REPAIRED":
            self.stdout.write(self.style.SUCCESS(line))
        elif case == "OK":
            self.stdout.write(line)
        else:
            self.stdout.write(self.style.WARNING(line))
