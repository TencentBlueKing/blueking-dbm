# Generated by Django 3.2.25 on 2024-06-21 04:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ticket", "0008_alter_ticketflowsconfig_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="flow",
            options={"verbose_name": "单据流程(Flow)", "verbose_name_plural": "单据流程(Flow)"},
        ),
        migrations.AlterModelOptions(
            name="ticket",
            options={"ordering": ("-id",), "verbose_name": "单据(Ticket)", "verbose_name_plural": "单据(Ticket)"},
        ),
        migrations.AlterModelOptions(
            name="ticketflowsconfig",
            options={"verbose_name": "单据流程配置(TicketFlowsConfig)", "verbose_name_plural": "单据流程配置(TicketFlowsConfig)"},
        ),
        migrations.AlterModelOptions(
            name="todo",
            options={"verbose_name": "待办(Todo)", "verbose_name_plural": "待办(Todo)"},
        ),
    ]
