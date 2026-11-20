from django.db import migrations

# 固化迁移时核对过的流程规则。只修正能够确定的字段，保留依赖配置或提单参数的值。
PRESET_CONFIG_CORRECTIONS = {
    **{
        ticket_type: {"need_itsm": False}
        for ticket_type in (
            "CLOUD_DBHA_ADD",
            "CLOUD_DBHA_REDUCE",
            "CLOUD_DBHA_RELOAD",
            "CLOUD_DBHA_REPLACE",
            "CLOUD_DNS_ADD",
            "CLOUD_DNS_REDUCE",
            "CLOUD_DNS_RELOAD",
            "CLOUD_DNS_REPLACE",
            "CLOUD_DRS_ADD",
            "CLOUD_DRS_REDUCE",
            "CLOUD_DRS_RELOAD",
            "CLOUD_DRS_REPLACE",
            "CLOUD_NGINX_RELOAD",
            "CLOUD_NGINX_REPLACE",
            "CLOUD_REDIS_DTS_SERVER_ADD",
            "CLOUD_REDIS_DTS_SERVER_REDUCE",
        )
    },
    **{
        ticket_type: {"need_itsm": False, "need_manual_confirm": False}
        for ticket_type in (
            "CLOUD_SERVICE_APPLY",
            "MYSQL_AUTHORIZE_RULES",
            "MYSQL_EXCEL_AUTHORIZE_RULES",
            "RECYCLE_OLD_HOST",
            "SQLSERVER_AUTHORIZE_RULES",
            "SQLSERVER_EXCEL_AUTHORIZE_RULES",
            "TENDBCLUSTER_AUTHORIZE_RULES",
            "TENDBCLUSTER_EXCEL_AUTHORIZE_RULES",
        )
    },
    "RECYCLE_APPLY_HOST": {"need_itsm": False, "need_manual_confirm": True},
    "REDIS_BACKUP_AUTO": {"need_itsm": False, "need_manual_confirm": True},
    # MySQL 和 TenDB Cluster 是否审批取决于导出参数，人工确认节点固定存在。
    "MYSQL_DUMP_DATA": {"need_manual_confirm": True},
    "TENDBCLUSTER_DUMP_DATA": {"need_manual_confirm": True},
    "SQLSERVER_DATA_EXPORT": {"need_itsm": True, "need_manual_confirm": True},
}


def fix_preset_configs(apps, schema_editor):
    ticket_flows_config = apps.get_model("ticket", "TicketFlowsConfig")
    configs = ticket_flows_config.objects.using(schema_editor.connection.alias)
    targets = configs.select_for_update().filter(editable=False, ticket_type__in=PRESET_CONFIG_CORRECTIONS)
    for target in targets.iterator(chunk_size=200):
        corrected = PRESET_CONFIG_CORRECTIONS[target.ticket_type]
        # 只合并需要修正的两个开关，保留超时配置和其他字段。
        if any(target.configs.get(key) is not value for key, value in corrected.items()):
            target.configs = {**target.configs, **corrected}
            target.save(using=configs.db, update_fields=["configs"])


class Migration(migrations.Migration):
    dependencies = [("ticket", "0020_ticketsnapshot")]

    # 原值可能是错误的，回退 schema 时也保留已修正的配置。
    operations = [migrations.RunPython(fix_preset_configs, migrations.RunPython.noop, atomic=True)]
