import time

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.models import AppCache, Cluster
from backend.db_services.sqlserver.sql_import.constants import BKREPO_SQLSERVER_SQLFILE_PATH
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerBaseOperateDetailSerializer
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Flow


class SQLServerDataExportDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class DataExportDetailSerializer(serializers.Serializer):
        dbnames = serializers.ListField(help_text=_("导出库列表"), child=serializers.CharField())
        sql_files = serializers.ListField(help_text=_("SQL文件列表"), child=serializers.CharField())
        path = serializers.CharField(help_text=_("查询文件在制品库中的路径"), required=True)

    cluster_ids = serializers.ListField(help_text=_("查询集群列表"), child=serializers.IntegerField())
    execute_objects = serializers.ListField(help_text=_("执行对象列表"), child=serializers.DictField())
    select_role = serializers.ChoiceField(
        help_text=_("查询实例角色，master或 slave"),
        choices=[
            ("master", ""),
            ("slave", ""),
        ],
        required=False,
    )

    def validate(self, attrs):
        attrs = super(SQLServerBaseOperateDetailSerializer, self).validate(attrs)
        # 校验集群是否可用
        # 单据详情添加path字段信息
        attrs["path"] = BKREPO_SQLSERVER_SQLFILE_PATH.format(biz=self.context["bk_biz_id"])
        super().validate_cluster_can_access(attrs)
        return attrs


class SQLServerDataExportItsmMaintainerFlowParamsBuilder(builders.ItsmParamBuilder):
    def get_approvers(self):
        approvers = AppCache.get_app_attr_from_cc(self.ticket.bk_biz_id, attr_name="bk_biz_maintainer")
        return approvers or "admin"


class SQLServerDataExportItsmProductorFlowParamsBuilder(builders.ItsmParamBuilder):
    def get_approvers(self):
        approvers = AppCache.get_app_attr_from_cc(self.ticket.bk_biz_id, attr_name="bk_biz_productor")
        return approvers or "admin"


class SQLServerDataExportFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.sqlserver_data_export_scene

    # 文件名
    def format_ticket_data(self):
        self.ticket_data["path"] = BKREPO_SQLSERVER_SQLFILE_PATH.format(biz=self.ticket.bk_biz_id)
        cluster = Cluster.objects.filter(id__in=self.ticket_data["cluster_ids"])
        dump_file_name = f"{cluster.first().immute_domain}_{int(time.time())}_dbm_console_dump.sql"
        self.ticket_data["dump_file_name"] = dump_file_name

    def post_callback(self):
        flow = self.ticket.current_flow()
        # 如果流程树运行不为成功，则忽略
        if flow.status != TicketFlowStatus.SUCCEEDED:
            return
        # 往flow的detail中写入制品库的下载链接
        dump_file_name = f"{flow.details['ticket_data']['dump_file_name']}.zip"
        flow.details["ticket_data"].update(
            dump_file_name=dump_file_name,
            dump_file_path=f"{BKREPO_SQLSERVER_SQLFILE_PATH.format(biz=self.ticket.bk_biz_id)}/{dump_file_name}",
        )
        flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.SQLSERVER_DATA_EXPORT)
class SQLServerDataExportFlowBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerDataExportDetailSerializer
    inner_flow_builder = SQLServerDataExportFlowParamBuilder
    inner_flow_name = _("数据导出执行")
    itsm_flow_maintainer_builder = SQLServerDataExportItsmMaintainerFlowParamsBuilder
    itsm_flow_productor_builder = SQLServerDataExportItsmProductorFlowParamsBuilder
    editable = False

    def init_ticket_flows(self):
        flows = []

        # 二级审批（运维 + 产品)
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.BK_ITSM.value,
                details=self.itsm_flow_maintainer_builder(self.ticket).get_params(),
                flow_alias=_("运维人员审批"),
            )
        )
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.BK_ITSM.value,
                details=self.itsm_flow_productor_builder(self.ticket).get_params(),
                flow_alias=_("产品人员审批"),
            )
        )

        # 人工确认
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.PAUSE.value,
                details=self.pause_node_builder(self.ticket).get_params(),
                flow_alias=_("人工确认"),
            ),
        )

        # 数据导出
        flows.append(
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=self.inner_flow_builder(self.ticket).get_params(),
                flow_alias=self.inner_flow_name,
                retry_type=self.retry_type,
            )
        )

        # 批量创建所有流程
        Flow.objects.bulk_create(flows)
        # 返回该工单的所有流程对象
        return list(Flow.objects.filter(ticket=self.ticket))

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = [_("运维人员审批"), _("产品人员审批"), _("人工确认"), _("数据导出执行")]
        return flow_desc
