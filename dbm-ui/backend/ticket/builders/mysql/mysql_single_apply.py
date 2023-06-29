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
import collections
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.bk_web.constants import LEN_MIDDLE, SMALLEST_POSITIVE_INTEGER
from backend.components import DBConfigApi
from backend.components.dbconfig import constants as dbconf_const
from backend.configuration.constants import MASTER_DOMAIN_INITIAL_VALUE
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import DBModule
from backend.db_services.cmdb.biz import get_db_app_abbr
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mysql.constants import DEFAULT_ORIGIN_MYSQL_PORT, SERVER_PORT_LIMIT_MAX, SERVER_PORT_LIMIT_MIN
from backend.exceptions import ValidationError
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
from backend.ticket.exceptions import TicketParamsVerifyException
from backend.ticket.models import Flow


class DomainSerializer(serializers.Serializer):
    """
    域名信息序列化
    """

    # 此字段是集群名，可考虑跟前端一起调整为 cluster_name
    key = serializers.CharField(help_text=_("域名关键字"), max_length=LEN_MIDDLE)


class MysqlSingleApplyDetailSerializer(serializers.Serializer):
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    city_code = serializers.CharField(
        help_text=_("城市代码"), required=False, allow_blank=True, allow_null=True, default=""
    )
    spec = serializers.CharField(help_text=_("机器规格"), required=False, default="", allow_null=True, allow_blank=True)
    db_module_id = serializers.IntegerField(help_text=_("DB模块ID"))
    cluster_count = serializers.IntegerField(help_text=_("申请数量"), min_value=SMALLEST_POSITIVE_INTEGER)
    inst_num = serializers.IntegerField(
        help_text=_("每台机器部署的实例数量"), min_value=SMALLEST_POSITIVE_INTEGER, required=False, default=1
    )
    ip_source = serializers.ChoiceField(
        help_text=_("主机来源"), choices=IpSource.get_choices(), default=IpSource.RESOURCE_POOL.value
    )
    nodes = serializers.JSONField(help_text=_("部署节点"), required=False)
    resource_spec = serializers.JSONField(help_text=_("部署规格"), required=False)
    domains = serializers.ListField(help_text=_("域名列表"), child=DomainSerializer())

    # display fields
    charset = serializers.SerializerMethodField(help_text=_("字符集"))
    db_version = serializers.SerializerMethodField(help_text=_("数据库版本"))
    db_module_name = serializers.SerializerMethodField(help_text=_("DB模块名"))
    city_name = serializers.SerializerMethodField(help_text=_("城市名"))
    spec_display = serializers.SerializerMethodField(help_text=_("机器规格展示名"))

    start_mysql_port = serializers.IntegerField(
        help_text=_("MySQL起始端口"),
        required=False,
        min_value=SERVER_PORT_LIMIT_MIN,
        max_value=SERVER_PORT_LIMIT_MAX,
        default=DEFAULT_ORIGIN_MYSQL_PORT,
    )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        self._format_domains(representation["domains"], instance)
        # TODO 缺少数据库版本和字符集，考虑封装 DBConfigHandler 来处理此类需求
        return representation

    def validate_domains(self, obj):
        # 域名关键字不允许重复
        # TODO 校验存量的域名是否存在重复
        keys = [domain["key"] for domain in obj]
        duplicates = [item for item, count in collections.Counter(keys).items() if count > 1]
        if duplicates:
            raise ValidationError(_("不允许存在重复的域名关键字[{duplicates}]").format(duplicates=",".join(duplicates)))
        return obj

    def get_db_module_name(self, obj):
        db_module_id = obj["db_module_id"]
        return self.context["ticket_ctx"].db_module_map.get(db_module_id) or f"db-module-{db_module_id}"

    def get_spec_display(self, obj):
        spec = obj["spec"]
        return self.context["ticket_ctx"].spec_map.get(spec, spec)

    def get_city_name(self, obj):
        city_code = obj["city_code"]
        return self.context["ticket_ctx"].city_map.get(city_code, city_code)

    def get_charset(self, obj):
        return obj["charset"]

    def get_db_version(self, obj):
        return obj["db_version"]

    def _format_domains(self, domains, instance):
        db_module_name = self.get_db_module_name(instance)
        bk_biz_id = self.context["ticket_ctx"].db_module_id__biz_id_map.get(instance["db_module_id"])
        db_app_abbr = self.context["ticket_ctx"].app_abbr_map.get(bk_biz_id, f"biz-{bk_biz_id}")
        for index, domain in enumerate(domains):
            domains[index]["master"] = MASTER_DOMAIN_INITIAL_VALUE.format(
                db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain["key"]
            )
        return domains


class MysqlSingleApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_single_apply_scene

    def format_cluster_domains(self) -> List[Dict[str, str]]:
        db_module_name = DBModule.objects.get(db_module_id=self.ticket_data["db_module_id"]).db_module_name
        db_app_abbr = get_db_app_abbr(self.ticket_data["bk_biz_id"])
        return [
            {
                "name": domain["key"],
                # 域名不允许出现 下划线"_" ，使用 连字符"-" 替换
                "master": MASTER_DOMAIN_INITIAL_VALUE.format(
                    db_module_name=db_module_name, db_app_abbr=db_app_abbr, cluster_name=domain["key"]
                ).replace("_", "-"),
            }
            for domain in self.ticket_data["domains"]
        ]

    @classmethod
    def insert_ip_into_apply_infos(cls, ticket_data, apply_infos: List[Dict]):
        # 适配手动输入和资源池导入的角色类型
        backend_nodes = ticket_data["nodes"]["backend"] or ticket_data["nodes"]["single"]
        for index, apply_info in enumerate(apply_infos):
            apply_info["new_ip"] = backend_nodes[index]

    def format_ticket_data(self):
        clusters = self.format_cluster_domains()
        inst_num = self.ticket.details["inst_num"]
        cluster_count = len(clusters)
        # 按需求的实例数量自动给集群分组
        # cluster_count // inst_num 得到满编实例的主机数量
        # cluster_count % inst_num 决定是否需要多一台不满编的主机
        apply_infos = [
            {"clusters": clusters[group_index * inst_num : (group_index + 1) * inst_num]}
            for group_index in range(0, cluster_count // inst_num + bool(cluster_count % inst_num))
        ]

        if self.ticket_data["ip_source"] == IpSource.MANUAL_INPUT:
            self.insert_ip_into_apply_infos(self.ticket.details, apply_infos)

        self.ticket_data.update(
            {
                "module": str(self.ticket.details["db_module_id"]),
                "city": self.ticket.details["city_code"],
                "apply_infos": apply_infos,
            }
        )


class MysqlSingleApplyResourceParamBuilder(builders.ResourceApplyParamBuilder):
    def post_callback(self):
        next_flow = self.ticket.next_flow()
        apply_infos = next_flow.details["ticket_data"]["apply_infos"]

        MysqlSingleApplyFlowParamBuilder.insert_ip_into_apply_infos(self.ticket.details, apply_infos)

        next_flow.details["ticket_data"].update(apply_infos=apply_infos)
        next_flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_SINGLE_APPLY)
class MysqlSingleApplyFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlSingleApplyDetailSerializer
    inner_flow_builder = MysqlSingleApplyFlowParamBuilder
    inner_flow_name = _("MySQL单节点部署执行")
    resource_apply_builder = MysqlSingleApplyResourceParamBuilder

    def patch_ticket_detail(self):
        # 补充数据库版本和字符集
        db_config = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": str(self.ticket.bk_biz_id),
                "level_name": dbconf_const.LevelName.MODULE,
                "level_value": str(self.ticket.details["db_module_id"]),
                "conf_file": dbconf_const.DEPLOY_FILE_NAME,
                "conf_type": dbconf_const.ConfType.DEPLOY,
                "namespace": ClusterType.TenDBSingle,
                "format": dbconf_const.FormatType.MAP,
            }
        )["content"]

        # 校验配置是否存在
        if not db_config.get("db_version") or not db_config.get("charset"):
            raise TicketParamsVerifyException(_("获取数据库字符集或版本失败，请检查获取参数, db_config: {}").format(db_config))

        self.ticket.update_details(db_version=db_config.get("db_version"), charset=db_config.get("charset"))
