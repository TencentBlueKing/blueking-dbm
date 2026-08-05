from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoDBTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, TicketType


class MongodbClusterStandardizeDetailSerializer(BaseMongoDBOperateDetailSerializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    cluster_ids = serializers.ListField(child=serializers.IntegerField())
    restart_exporter = serializers.BooleanField()


class MongodbClusterStandardizeFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.cluster_standardization


@builders.BuilderFactory.register(TicketType.MONGODB_CLUSTER_STANDARDIZE, iam=ActionEnum.MONGODB_MANAGE)
class MongodbClusterStandardizeFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongodbClusterStandardizeDetailSerializer
    inner_flow_builder = MongodbClusterStandardizeFlowParamBuilder
    inner_flow_name = _("MongoDB集群标准化")
    retry_type = FlowRetryType.MANUAL_RETRY
