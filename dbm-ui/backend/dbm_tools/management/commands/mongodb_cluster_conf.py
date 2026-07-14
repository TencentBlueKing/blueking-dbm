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

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from backend.flow.utils.mongodb.mongodb_cluster_conf_tool import (
    MIGRATE_FROM_M,
    MIGRATE_FROM_MM,
    MIGRATE_STATUS_DONE,
    MIGRATE_STATUS_PENDING,
    MongoClusterConfToolError,
    format_batch_migrate_report,
    format_inspect_report,
    format_list_domains_report,
    format_migrate_report,
    get_mongodb_cluster_by_domain,
    inspect_mongodb_cluster_conf,
    list_mongodb_cluster_conf_migrate_domains,
    migrate_mongodb_cluster_conf_by_domain,
    migrate_mongodb_cluster_conf_pending_batch,
)


class Command(BaseCommand):
    help = _("Query or migrate MongoDB CLUSTER-level dbconf by cluster_domain (immute_domain)")

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action", required=True)

        query_parser = subparsers.add_parser("query", help=_("Inspect dbconf for a MongoDB cluster"))
        query_parser.add_argument("cluster_domain", type=str, help=_("Cluster immute_domain"))
        query_parser.add_argument(
            "--version",
            type=str,
            default=None,
            help=_("Version used for conf_file probe (default: cluster.major_version)"),
        )
        query_parser.add_argument("--json", action="store_true", help=_("Output JSON"))

        list_pending_parser = subparsers.add_parser(
            "list-pending",
            help=_(
                "List domains pending dbconf migrate "
                "(versioned CLUSTER conf mongodb-*/Mongodb-* and/or legacy level_value)"
            ),
        )
        list_pending_parser.add_argument(
            "--bk-biz-id",
            type=int,
            default=None,
            help=_("Filter by business id (default: all MongoDB clusters)"),
        )
        list_pending_parser.add_argument("--json", action="store_true", help=_("Output JSON"))

        list_done_parser = subparsers.add_parser(
            "list-done",
            help=_("List domains already migrated (no versioned CLUSTER conf, no legacy level_value)"),
        )
        list_done_parser.add_argument(
            "--bk-biz-id",
            type=int,
            default=None,
            help=_("Filter by business id (default: all MongoDB clusters)"),
        )
        list_done_parser.add_argument("--json", action="store_true", help=_("Output JSON"))

        migrate_parser = subparsers.add_parser(
            "migrate",
            help=_("Migrate CLUSTER dbconf (level_value name->domain first, then conf_file)"),
        )
        migrate_parser.add_argument(
            "cluster_domain",
            type=str,
            nargs="?",
            default=None,
            help=_("Cluster immute_domain (omit when using --limit)"),
        )
        migrate_parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help=_(
                "Migrate first N pending domains (id asc); requires --to-role --from; "
                "mutually exclusive with domain"
            ),
        )
        migrate_parser.add_argument(
            "--bk-biz-id",
            type=int,
            default=None,
            help=_("With --limit: filter pending list by business id"),
        )
        migrate_parser.add_argument(
            "--to-role",
            action="store_true",
            help=_(
                "Migrate versioned conf_file into role conf_files "
                "(mongod.conf or shardsvr.conf/configsvr.conf/mongos.conf); requires --from; "
                "also fill cluster.major_version / instance.version to mongodb-x.y.z when needed"
            ),
        )
        migrate_parser.add_argument(
            "--from",
            dest="from_kind",
            choices=[MIGRATE_FROM_MM, MIGRATE_FROM_M],
            default=None,
            help=_("With --to-role: source versioned conf_file kind — " "mm=mongodb-x.y, M=Mongodb-x"),
        )
        migrate_parser.add_argument(
            "--target-version",
            type=str,
            default=None,
            help=_("Target/source version hint, e.g. mongodb-7.0 (optional with --to-role)"),
        )
        migrate_parser.add_argument(
            "--source-version",
            type=str,
            default=None,
            help=_("Source version (default: cluster.major_version; not used with --to-role)"),
        )
        migrate_parser.add_argument("--apply", action="store_true", help=_("Apply migration (default: dry-run)"))
        migrate_parser.add_argument(
            "--force",
            action="store_true",
            help=_("Overwrite when target level_value already owns the same conf_file"),
        )
        migrate_parser.add_argument("--json", action="store_true", help=_("Output JSON"))

    def handle(self, *args, **options):
        action = options["action"]
        try:
            if action == "query":
                self._handle_query(options)
            elif action == "list-pending":
                self._handle_list(options, status=MIGRATE_STATUS_PENDING)
            elif action == "list-done":
                self._handle_list(options, status=MIGRATE_STATUS_DONE)
            elif action == "migrate":
                self._handle_migrate(options)
        except MongoClusterConfToolError as err:
            raise CommandError(str(err)) from err

    def _handle_query(self, options):
        cluster = get_mongodb_cluster_by_domain(options["cluster_domain"])
        report = inspect_mongodb_cluster_conf(cluster, version=options.get("version"))
        if options.get("json"):
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(format_inspect_report(report))

    def _handle_list(self, options, *, status: str):
        entries = list_mongodb_cluster_conf_migrate_domains(
            status=status,
            bk_biz_id=options.get("bk_biz_id"),
        )
        if options.get("json"):
            self.stdout.write(json.dumps(entries, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(format_list_domains_report(entries, status=status))

    def _handle_migrate(self, options):
        cluster_domain = options.get("cluster_domain")
        limit = options.get("limit")
        to_role = options.get("to_role")
        from_kind = options.get("from_kind")

        if limit is not None and cluster_domain:
            raise CommandError("cluster_domain and --limit are mutually exclusive")
        if limit is None and not cluster_domain:
            raise CommandError("cluster_domain or --limit is required")
        if options.get("source_version") and to_role:
            raise CommandError("--source-version cannot be used with --to-role")
        if to_role and not from_kind:
            raise CommandError("--to-role requires --from mm|M")
        if from_kind and not to_role:
            raise CommandError("--from requires --to-role")

        if limit is not None:
            if not to_role:
                raise CommandError("--limit requires --to-role --from")
            if options.get("target_version") or options.get("source_version"):
                raise CommandError("--target-version/--source-version cannot be used with --limit")
            batch = migrate_mongodb_cluster_conf_pending_batch(
                limit=limit,
                from_kind=from_kind,
                bk_biz_id=options.get("bk_biz_id"),
                dry_run=not options.get("apply"),
                force=options.get("force"),
            )
            if options.get("json"):
                self.stdout.write(json.dumps(batch, ensure_ascii=False, indent=2))
            else:
                self.stdout.write(format_batch_migrate_report(batch))
            return

        if not to_role and not options.get("target_version"):
            raise CommandError("--target-version is required unless --to-role is set")
        if options.get("bk_biz_id") is not None:
            raise CommandError("--bk-biz-id is only valid with --limit")

        report = migrate_mongodb_cluster_conf_by_domain(
            cluster_domain=cluster_domain,
            target_version=options.get("target_version"),
            source_version=options.get("source_version"),
            dry_run=not options.get("apply"),
            to_role=to_role,
            from_kind=from_kind,
            force=options.get("force"),
        )
        if options.get("json"):
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(format_migrate_report(report))
