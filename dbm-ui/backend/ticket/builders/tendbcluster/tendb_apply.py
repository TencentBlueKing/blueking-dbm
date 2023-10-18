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


from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.components import DBConfigApi
from backend.components.dbconfig import constants as dbconf_const
from backend.db_meta.enums import ClusterType
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class TenDBClusterApplyDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    db_app_abbr = serializers.CharField(help_text=_("业务英文缩写"))
    cluster_name = serializers.CharField(help_text=_("集群名"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL.value
    )
    resource_spec = serializers.JSONField(help_text=_("部署规格"))
    spider_port = serializers.IntegerField(help_text=_("集群访问端口"))
    cluster_shard_num = serializers.IntegerField(help_text=_("集群分片数"))
    remote_shard_num = serializers.IntegerField(help_text=_("单机分片数"))

    # display fields
    bk_cloud_name = serializers.SerializerMethodField(help_text=_("云区域"))
    charset = serializers.SerializerMethodField(help_text=_("字符集"))
    version = serializers.SerializerMethodField(help_text=_("数据库版本"))
    db_module_name = serializers.SerializerMethodField(help_text=_("DB模块名"))
    city_name = serializers.SerializerMethodField(help_text=_("城市名"))
    machine_pair_cnt = serializers.SerializerMethodField(help_text=_("机器组数"))

    def get_bk_cloud_name(self, obj):
        clouds = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return clouds[str(obj["bk_cloud_id"])]["bk_cloud_name"]

    def get_charset(self, obj):
        return obj["charset"]

    def get_version(self, obj):
        return {"db_version": obj["db_version"], "spider_version": obj["spider_version"]}

    def get_db_module_name(self, obj):
        db_module_id = obj["db_module_id"]
        return self.context["ticket_ctx"].db_module_map.get(db_module_id) or f"db-module-{db_module_id}"

    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def get_machine_pair_cnt(self, obj):
        return obj["cluster_shard_num"] / obj["remote_shard_num"]

    def validate(self, attrs):
        # 校验集群域名合法
        CommonValidate.validate_generate_domain("spider", attrs["cluster_name"], attrs["db_app_abbr"])
        CommonValidate.validate_generate_domain("spider-slave", attrs["cluster_name"], attrs["db_app_abbr"])
        # TODO: spider集群部署校验
        # 校验集群名是否重复
        CommonValidate.validate_duplicate_cluster_name(
            self.context["bk_biz_id"], self.context["ticket_type"], attrs["cluster_name"]
        )
        return attrs


class TenDBClusterApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.spider_cluster_apply_scene

    def format_ticket_data(self):
        # 补充resource_spec信息
        self.ticket_data.update(
            module=str(self.ticket.details["db_module_id"]),
            city=self.ticket.details["city_code"],
            immutable_domain=f"spider.{self.ticket_data['cluster_name']}.{self.ticket_data['db_app_abbr']}.db",
        )


class TenDBClusterApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        nodes = next_flow.details["ticket_data"].pop("nodes")
        resource_spec = next_flow.details["ticket_data"]["resource_spec"]

        # 格式化后台角色信息
        resource_spec["remote"], __ = resource_spec.pop("master"), resource_spec.pop("slave")
        next_flow.details["ticket_data"].update(
            spider_ip_list=nodes["spider"], remote_group=nodes["backend_group"], resource_spec=resource_spec
        )
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_APPLY, is_apply=True, cluster_type=ClusterType.TenDBCluster)
class TenDBClusterApplyFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TenDBClusterApplyDetailSerializer
    inner_flow_builder = TenDBClusterApplyFlowParamBuilder
    inner_flow_name = _("TenDB Cluster 集群部署执行")
    resource_apply_builder = TenDBClusterApplyResourceParamBuilder

    def patch_ticket_detail(self):
        """补充spider申请的需求信息参数"""
        details = self.ticket.details
        # 补充字符集和版本信息
        db_config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket.bk_biz_id),
                "level_name": dbconf_const.LevelName.MODULE,
                "level_value": str(details["db_module_id"]),
                "conf_file": dbconf_const.DEPLOY_FILE_NAME,
                "conf_type": dbconf_const.ConfType.DEPLOY,
                "namespace": ClusterType.TenDBCluster,
                "format": dbconf_const.FormatType.MAP,
            }
        )["content"]
        details.update(
            charset=db_config.get("charset"),
            db_version=db_config.get("db_version"),
            spider_version=db_config.get("spider_version"),
        )

        self.ticket.save(update_fields=["details"])

    @property
    def need_itsm(self):
        return True
