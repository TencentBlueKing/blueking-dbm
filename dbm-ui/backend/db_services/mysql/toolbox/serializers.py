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
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.engine.controller.spider import SpiderController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, TicketType


class QuerySpiderPkgListByCompareVersionSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField()
    higher_major_version = serializers.BooleanField(default=False)
    higher_sub_version = serializers.BooleanField(default=False)

    class Meta:
        swagger_schema_fields = {"cluster_id": 123, "higher_major_version": False, "higher_sub_version": False}


class QueryPkgListByCompareVersionSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField()
    higher_major_version = serializers.BooleanField(default=False)
    higher_all_version = serializers.BooleanField(default=False)

    class Meta:
        swagger_schema_fields = {"cluster_id": 123, "higher_major_version": False, "higher_all_version": False}


class TendbhaTransferToOtherBizSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("源业务ID"))
    target_biz_id = serializers.IntegerField(help_text=_("目标业务ID"))
    cluster_domain_list = serializers.ListField(child=serializers.CharField())
    db_module_id = serializers.IntegerField()
    need_clone_priv_rules = serializers.BooleanField(default=False)

    class Meta:
        swagger_schema_fields = {
            "bk_biz_id": 11,
            "target_biz_id": 123,
            "cluster_domain_list": [],
            "db_module_id": 123,
            "need_clone_priv_rules": False,
        }


class TendbhaTransferToOtherBizFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.tranfer_biz_scene


@builders.BuilderFactory.register(TicketType.MYSQL_HA_TRANSFER_TO_OTHER_BIZ)
class TendbhaTransferToOtherBizFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbhaTransferToOtherBizSerializer
    inner_flow_builder = TendbhaTransferToOtherBizFlowParamBuilder
    inner_flow_name = _("TenDBHa集群迁移到其他业务")
    retry_type = FlowRetryType.MANUAL_RETRY


class TendbhaAddSlaveDomainSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群id"))
    slave_ip = serializers.CharField(help_text=_("slave ip"))
    slave_port = serializers.IntegerField(help_text=_("slave port"))
    domain_name = serializers.CharField(help_text=_("slave domain"))

    class Meta:
        swagger_schema_fields = {
            "bk_biz_id": 11,
            "slave_ip": "1.1.1.1",
            "slave_port": 3306,
            "domain_name": "",
        }


class ChangeClusterSpecSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    cluster_type = serializers.ChoiceField(
        choices=["tendbha", "tendbcluster"], help_text=_("集群类型: tendbha 或 tendbcluster")
    )
    spec_id = serializers.IntegerField(help_text=_("规格ID"))
    machine_type = serializers.CharField(help_text=_("机器类型"))


class GetSpiderVersionModulesSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    higher_major_version = serializers.BooleanField(default=False, help_text=_("是否查找更高主版本的模块"))
    higher_sub_version = serializers.BooleanField(default=False, help_text=_("是否查找同大版本但子版本更高的模块"))

    class Meta:
        swagger_schema_fields = {
            "cluster_id": 123,
            "cluster_type": "tendbha",
            "spec_id": 456,
            "machine_type": "storage",
            "higher_major_version": False,
            "higher_sub_version": False,
        }


class GetStorageVersionModulesSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    higher_major_version = serializers.BooleanField(default=False, help_text=_("是否查找更高主版本的模块"))
    higher_sub_version = serializers.BooleanField(default=False, help_text=_("是否查找同大版本但子版本更高的模块"))

    class Meta:
        swagger_schema_fields = {
            "cluster_id": 96,
            "higher_major_version": True,
            "higher_sub_version": False,
        }


class RollbackHostSerializer(serializers.Serializer):
    """回档主机序列化器"""

    ip = serializers.CharField(help_text=_("IP地址"), required=True)
    bk_host_id = serializers.IntegerField(help_text=_("主机ID"), required=True)
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=True)


class MySQLRollbackExerciseByClusterSerializer(serializers.Serializer):
    """MySQL回档演练按集群序列化器"""

    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=True)
    pause_after_restore = serializers.BooleanField(help_text=_("是否在恢复后暂停"), required=True)
    rollback_host = RollbackHostSerializer(help_text=_("回档主机信息"), required=True)
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=True)
    backup_id = serializers.CharField(help_text=_("备份ID"), required=False, allow_blank=True, allow_null=True)


class MysqlDiskSpace(serializers.Serializer):
    """
    mysql 磁盘空间估算
    """

    class DataMigrateInfoSerializer(serializers.Serializer):
        source_cluster = serializers.IntegerField(help_text=_("源集群ID"))
        target_clusters = serializers.ListField(help_text=_("目标集群列表"), child=serializers.IntegerField())
        db_list = serializers.ListField(help_text=_("最终库列表"), child=serializers.CharField())
        data_schema_grant = serializers.CharField(help_text=_("克隆类型"), required=False, default="data,schema")
        clone_db_list = serializers.ListField(help_text=_("克隆库列表"), child=serializers.CharField(), required=False)
        ignore_db_list = serializers.ListField(
            help_text=_("忽略db列表"), child=serializers.CharField(allow_blank=True), required=False
        )

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    factor = serializers.IntegerField(help_text=_("标识"))
    migrations = serializers.ListSerializer(help_text=_("集群信息"), child=DataMigrateInfoSerializer())


# ============== TdbCtl 升级相关序列化器 ==============


class TdbctlUpgradeScheduleSerializer(serializers.Serializer):
    """TdbCtl 升级调度序列化器"""

    pkg_id = serializers.IntegerField(help_text=_("tdbctl 升级包ID"), required=True)
    bk_biz_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("业务ID列表，为空则升级全部业务"),
        required=False,
        default=None,
        allow_null=True,
    )
    batch_size = serializers.IntegerField(
        help_text=_("每批集群数量"),
        required=False,
        default=20,
        min_value=1,
        max_value=100,
    )
    schedule_interval_seconds = serializers.IntegerField(
        help_text=_("每个业务之间的调度间隔（秒）"),
        required=False,
        default=180,
        min_value=0,
        max_value=3600,
    )

    class Meta:
        swagger_schema_fields = {
            "pkg_id": 123,
            "bk_biz_ids": [1, 2, 3],
            "batch_size": 20,
            "schedule_interval_seconds": 180,
        }


class TdbctlUpgradeProgressSerializer(serializers.Serializer):
    """TdbCtl 升级进度查询序列化器"""

    pkg_id = serializers.IntegerField(help_text=_("tdbctl 升级包ID"), required=True)
    bk_biz_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("业务ID列表，为空则查询全部业务"),
        required=False,
        default=None,
        allow_null=True,
    )

    class Meta:
        swagger_schema_fields = {
            "pkg_id": 123,
            "bk_biz_ids": [1, 2, 3],
        }


class TdbctlUpgradeRecordsSerializer(serializers.Serializer):
    """TdbCtl 升级记录查询序列化器"""

    pkg_id = serializers.IntegerField(help_text=_("tdbctl 升级包ID"), required=True)
    bk_biz_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("业务ID列表，为空则查询全部业务"),
        required=False,
        default=None,
        allow_null=True,
    )
    status = serializers.CharField(help_text=_("状态过滤"), required=False, allow_blank=True, allow_null=True)
    cluster_id = serializers.IntegerField(help_text=_("集群ID过滤"), required=False, allow_null=True)
    limit = serializers.IntegerField(help_text=_("返回记录数"), required=False, default=100, min_value=1, max_value=500)
    offset = serializers.IntegerField(help_text=_("偏移量"), required=False, default=0, min_value=0)

    class Meta:
        swagger_schema_fields = {
            "pkg_id": 123,
            "bk_biz_ids": [1, 2, 3],
            "status": "success",
            "cluster_id": 456,
            "limit": 100,
            "offset": 0,
        }


class TdbctlUpgradeSerializer(serializers.Serializer):
    """TdbCtl 同步升级序列化器"""

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=True)
    cluster_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("集群ID列表"),
        required=False,
        default=list,
        allow_empty=True,
    )
    pkg_id = serializers.IntegerField(help_text=_("tdbctl 升级包ID"), required=True)
    upgrade_all = serializers.BooleanField(
        help_text=_("是否升级业务下所有 spider 集群"),
        required=False,
        default=False,
    )

    class Meta:
        swagger_schema_fields = {
            "bk_biz_id": 100,
            "cluster_ids": [1, 2, 3],
            "pkg_id": 123,
            "upgrade_all": False,
        }

    def validate(self, attrs):
        """
        校验是否存在需要升级的集群

        校验逻辑：
        1. 校验参数：cluster_ids 和 upgrade_all 至少提供一个
        2. 查询待升级的集群
        3. 过滤出真正需要升级的集群（排除版本已是最新的）
        4. 如果没有需要升级的集群，抛出 ValidationError
        """
        from backend.db_services.mysql.toolbox.tdbctl_upgrade_handler import TdbctlUpgradeHandler

        bk_biz_id = attrs.get("bk_biz_id")
        cluster_ids = attrs.get("cluster_ids", [])
        pkg_id = attrs.get("pkg_id")
        upgrade_all = attrs.get("upgrade_all", False)

        # 1. 校验参数：cluster_ids 和 upgrade_all 至少提供一个
        if not upgrade_all and not cluster_ids:
            raise serializers.ValidationError(_("cluster_ids 和 upgrade_all 至少提供一个"))

        # 2. 使用 TdbctlUpgradeHandler 校验集群
        try:
            handler = TdbctlUpgradeHandler(
                bk_biz_id=bk_biz_id,
                pkg_id=pkg_id,
                operator="validator",  # 校验阶段使用占位符
            )

            # 3. 获取待升级的集群列表
            clusters = handler.get_clusters_to_upgrade(cluster_ids=cluster_ids, upgrade_all=upgrade_all)

            if not clusters:
                raise serializers.ValidationError(_("没有找到需要升级的 spider 集群"))

            # 4. 过滤出真正需要升级的集群
            filter_result = handler.filter_clusters_need_upgrade(clusters)
            upgraded_clusters = filter_result["upgraded_clusters"]
            skipped_clusters = filter_result["skipped_clusters"]

            if not upgraded_clusters:
                # 构建详细的错误消息
                skipped_info = ", ".join(
                    [
                        "{}({})".format(item["cluster_domain"], item["reason"])
                        for item in skipped_clusters[:5]  # 最多显示5个
                    ]
                )
                if len(skipped_clusters) > 5:
                    skipped_info += _("等 {} 个集群").format(len(skipped_clusters))

                raise serializers.ValidationError(_("所有集群版本已是最新或无法升级，无需升级。跳过的集群: {}").format(skipped_info))

        except ValueError as e:
            # TdbctlUpgradeHandler 抛出的参数错误
            raise serializers.ValidationError(str(e))
        except Exception as e:
            # 其他异常
            raise serializers.ValidationError(_("校验集群时发生错误: {}").format(str(e)))

        return attrs


class TdbctlUpgradeFlowParamBuilder(builders.FlowParamBuilder):
    controller = SpiderController.tendbcluster_tdbctl_upgrade

    def format_ticket_data(self):
        """
        格式化单据数据，将单据参数转换为 Flow 期望的格式

        单据参数格式：
        {
            "bk_biz_id": 100,
            "cluster_ids": [1, 2, 3],
            "pkg_id": 123,
            "upgrade_all": False
        }

        Flow 期望格式：
        {
            "bk_biz_id": 100,
            "bk_cloud_id": 0,
            "uid": "admin",
            "infos": [
                {"cluster_id": 1, "pkg_id": 123},
                {"cluster_id": 2, "pkg_id": 123},
                {"cluster_id": 3, "pkg_id": 123}
            ]
        }
        """
        from backend.db_meta.models import Cluster

        # 2. 转换参数结构：cluster_ids + pkg_id -> infos 列表
        cluster_ids = self.ticket_data.pop("cluster_ids", [])
        pkg_id = self.ticket_data.get("pkg_id")
        # 指定集群升级，构建 infos 列表
        self.ticket_data["infos"] = [{"cluster_id": cluster_id, "pkg_id": pkg_id} for cluster_id in cluster_ids]

        # 3. 添加 bk_cloud_id 字段
        # 从第一个集群获取 bk_cloud_id（同一业务下的 spider 集群通常在同一云区域）
        if cluster_ids:
            first_cluster = Cluster.objects.filter(id=cluster_ids[0]).first()
            if first_cluster:
                self.ticket_data["bk_cloud_id"] = first_cluster.bk_cloud_id
            else:
                self.ticket_data["bk_cloud_id"] = 0
        else:
            # 全量升级时，使用默认云区域
            self.ticket_data["bk_cloud_id"] = 0


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_TDBCTL_UPGRADE, iam=ActionEnum.TENDBCLUSTER_MANAGE)
class TdbctlUpgradeFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TdbctlUpgradeSerializer
    inner_flow_builder = TdbctlUpgradeFlowParamBuilder
    inner_flow_name = _("TdbCtl 升级")
    retry_type = FlowRetryType.MANUAL_RETRY
