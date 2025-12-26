from django.core.management.base import BaseCommand, CommandError

from backend.components.dbconfig.sync_dbconfig import sync_dbconfig


class Command(BaseCommand):
    help = "从本地 JSON 文件同步配置到 DB (sync_dbconfig)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--namespace",
            type=str,
            help="指定同步的 namespace (不指定则同步所有)",
        )
        parser.add_argument(
            "--conf-type",
            dest="conf_type",
            type=str,
            help="指定同步的 conf_type (不指定则同步所有)",
        )
        parser.add_argument(
            "--conf-file",
            dest="conf_file",
            type=str,
            help="指定同步的 conf_file (不指定则同步所有)",
        )

    def handle(self, *args, **options):
        namespace = options.get("namespace")
        conf_type = options.get("conf_type")
        conf_file = options.get("conf_file")

        self.stdout.write(self.style.SUCCESS("开始同步配置..."))

        try:
            sync_dbconfig(namespace=namespace, conf_type=conf_type, conf_file=conf_file)

            self.stdout.write(self.style.SUCCESS("配置同步完成。"))
        except Exception as e:
            self.stdout.write(self.style.ERROR("配置同步失败。"))
            raise CommandError(f"同步失败: {e}")
