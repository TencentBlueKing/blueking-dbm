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
import itertools
from collections import defaultdict

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class MySQLDataMigrateDetailSerializer(MySQLBaseOperateDetailSerializer):
    class DataMigrateInfoSerializer(serializers.Serializer):
        source_cluster = serializers.IntegerField(help_text=_("源集群ID"))
        target_clusters = serializers.ListField(help_text=_("目标集群列表"), child=serializers.IntegerField())
        db_list = serializers.ListField(help_text=_("迁移库列表"), child=serializers.CharField())

    infos = serializers.ListField(help_text=_("数据迁移信息"), child=DataMigrateInfoSerializer())

    def validate(self, attrs):
        # 获取目标集群的库信息
        cluster_ids = [[*info["target_clusters"], info["source_cluster"]] for info in attrs["infos"]]
        cluster_ids = list(itertools.chain(*cluster_ids))
        dbs_infos = RemoteServiceHandler(self.context["bk_biz_id"]).show_databases(cluster_ids)
        cluster_id__dbs_map = {item["cluster_id"]: item["databases"] for item in dbs_infos}

        target_cluster__db_list_map = defaultdict(list)
        for info in attrs["infos"]:
            source_cluster_dbs = cluster_id__dbs_map[info["source_cluster"]]

            # 迁移的数据库需要属于源集群
            if not set(source_cluster_dbs).issuperset(set(info["db_list"])):
                raise serializers.ValidationError(_("迁移存在不属于源集群的数据库"))

            for target_cluster in info["target_clusters"]:
                target_cluster_dbs = cluster_id__dbs_map[target_cluster]
                # 迁移的数据库不能与目标集群有交集
                if set(target_cluster_dbs).intersection(set(info["db_list"])):
                    raise serializers.ValidationError(_("迁移的数据库不能与目标集群有交集"))
                # target_cluster --- db 组成唯一键
                if set(target_cluster__db_list_map[target_cluster]).intersection(set(info["db_list"])):
                    raise serializers.ValidationError(_("即将迁移的数据库和目标集群不允许重复"))
                target_cluster__db_list_map[target_cluster].extend(info["db_list"])

        return attrs


class MySQLDataMigrateFlowParamBuilder(builders.FlowParamBuilder):
    """MySQL 数据校验执行单据参数"""

    controller = MySQLController.mysql_data_migrate_scene

    def format_ticket_data(self):
        # 1. 聚合源集群和迁移DB，value是目标集群列表
        source__migrate_dbs__target = defaultdict(lambda: defaultdict(set))
        for info in self.ticket_data["infos"]:
            for db in info["db_list"]:
                source__migrate_dbs__target[info["source_cluster"]][db].update(info["target_clusters"])

        # 2. 聚合源集群和目标集群列表，value是迁移db列表
        source__targets__migrate_dbs = defaultdict(lambda: defaultdict(set))
        for source, db_info in source__migrate_dbs__target.items():
            for db, targets in db_info.items():
                targets_key = ",".join(list(map(str, sorted(targets))))
                source__targets__migrate_dbs[source][targets_key].add(db)

        # 3. 取出聚合的迁移信息
        migrate_infos = []
        for source, target_info in source__targets__migrate_dbs.items():
            for targets, dbs in target_info.items():
                target_clusters = list(map(int, targets.split(",")))
                migrate_infos.append(
                    {"source_cluster": source, "target_clusters": target_clusters, "db_list": list(dbs)}
                )

        self.ticket_data["infos"] = migrate_infos


@builders.BuilderFactory.register(TicketType.MYSQL_DATA_MIGRATE)
class MySQLDataMigrateFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLDataMigrateDetailSerializer
    inner_flow_builder = MySQLDataMigrateFlowParamBuilder
    inner_flow_name = _("数据迁移执行")
