from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_report.enums.mysql_exporter_check_sub_type import MysqlExporterCheckSubType
from backend.db_report.report_basemodel import BaseReportABS


class MysqlExporterCheckReport(BaseReportABS):
    cluster = models.CharField(max_length=255, default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")
    subtype = models.CharField(
        max_length=64, choices=MysqlExporterCheckSubType.get_choices(), default="", help_text=_("exporter检查子项")
    )
    instance = models.CharField(max_length=255, default="", help_text=_("实例地址"))

    class Meta:
        managed = True
        app_label = "db_report"
        # 添加索引
        index_together = [["cluster", "subtype"], ["cluster", "instance"]]
