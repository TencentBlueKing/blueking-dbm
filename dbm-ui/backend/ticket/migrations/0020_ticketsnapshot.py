# Generated manually for 改单能力(ticket modify) scaffolding
# 内容版本号不新增 Ticket 字段，由 TicketSnapshot 记录数派生(modify.py: TicketModifyHandler._current_version)

from django.db import migrations, models

import backend.ticket.constants


class Migration(migrations.Migration):

    dependencies = [
        ("ticket", "0019_migrate_ticketflowsconfig_cluster_ids"),
    ]

    operations = [
        migrations.CreateModel(
            name="TicketSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("creator", models.CharField(max_length=64, verbose_name="创建人")),
                ("create_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updater", models.CharField(max_length=64, verbose_name="修改人")),
                ("update_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("ticket_id", models.IntegerField(db_index=True, verbose_name="关联工单ID")),
                ("flow_id", models.IntegerField(default=0, verbose_name="关联流程节点ID")),
                (
                    "mode",
                    models.CharField(
                        choices=backend.ticket.constants.TicketModifyType.get_choices(),
                        max_length=32,
                        verbose_name="改单模式",
                    ),
                ),
                ("operator", models.CharField(default="", max_length=64, verbose_name="操作人")),
                ("remark", models.CharField(default="", max_length=512, verbose_name="说明")),
                ("details", models.JSONField(default=dict, verbose_name="改单详情(前端传入未初始化的详情)")),
                ("change_count", models.IntegerField(default=0, verbose_name="差异字段数")),
            ],
            options={
                "verbose_name": "单据改单快照(TicketSnapshot)",
                "verbose_name_plural": "单据改单快照(TicketSnapshot)",
            },
        ),
    ]
