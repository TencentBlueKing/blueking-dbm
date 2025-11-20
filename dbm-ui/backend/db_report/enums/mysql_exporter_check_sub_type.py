from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class MysqlExporterCheckSubType(StrStructuredEnum):
    MysqldExporterUp = EnumField("mysqld_exporter_up", _("mysqld_exporter上报检查"))
    MysqlproxyExporterUp = EnumField("mysqlproxy_exporter_up", _("mysqlproxy_exporter上报检查"))
