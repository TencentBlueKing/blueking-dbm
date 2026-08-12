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
import logging

from django.utils.translation import gettext as gettext_runtime
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, Machine, MysqlDtsCluster
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.utils.mysql.dts.constants import (
    DtsLifecycleMode,
    FullLoadEngine,
    MigrateTopology,
    get_default_deploy_path,
)
from backend.flow.utils.mysql.dts.migrate_credentials import parse_dts_migrate_major_version
from backend.flow.utils.mysql.dts.migrate_plan import build_migrate_plan
from backend.flow.utils.mysql.dts.task_name import patch_migrate_task_names_into_details
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


class DtsHostSpecSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("主机IP"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    name = serializers.CharField(required=False, allow_blank=True, help_text=_("节点名称"))


class TableRouteSerializer(serializers.Serializer):
    """库表路由（对应 DTS routes / table_migrate_rule）。"""

    source_name = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("源名称（可选）"))
    source_db = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("源库名"))
    source_db_pattern = serializers.CharField(
        required=False, allow_blank=True, default="", help_text=_("源库通配（优先于 source_db）")
    )
    source_table = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("源表名"))
    source_table_pattern = serializers.CharField(
        required=False, allow_blank=True, default="", help_text=_("源表通配（优先于 source_table）")
    )
    target_db = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("目标库名（可选）"))
    target_table = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("目标表名（可选）"))


class SyncScopeSerializer(serializers.Serializer):
    do_dbs = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    ignore_dbs = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    do_tables = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    ignore_tables = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    table_routes = serializers.ListField(child=TableRouteSerializer(), required=False, default=list)
    binlog_filters = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class MyloaderSpecSerializer(serializers.Serializer):
    """myloader 全量导入参数（full_load.engine=myloader 时使用）。"""

    backup_id = serializers.CharField(required=False, allow_blank=True, help_text=_("指定备份 ID（可选，默认取最新逻辑全备）"))
    backup_source = serializers.CharField(
        required=False, allow_blank=True, default="remote", help_text=_("备份源: remote | local")
    )
    myloader_path = serializers.CharField(required=False, allow_blank=True, help_text=_("myloader 可执行文件路径（可选）"))
    myloader_dir = serializers.CharField(required=False, allow_blank=True, help_text=_("全备落盘目录（可选，默认由 Flow 下发）"))
    threads = serializers.IntegerField(required=False, default=16, min_value=1, help_text=_("并发线程数"))
    regex = serializers.CharField(required=False, allow_blank=True, help_text=_("库表过滤 regex（可选）"))
    sourcedb = serializers.CharField(required=False, allow_blank=True, help_text=_("--source-db（可选）"))
    tablelist = serializers.CharField(required=False, allow_blank=True, help_text=_("--tables-list（可选）"))
    setnames = serializers.CharField(required=False, allow_blank=True, help_text=_("--set-names（可选）"))
    defaultsfile = serializers.CharField(required=False, allow_blank=True, help_text=_("defaults-file 路径（可选）"))
    extraargs = serializers.CharField(required=False, allow_blank=True, help_text=_("额外参数（可选）"))
    dest_worker_ip = serializers.CharField(required=False, allow_blank=True, help_text=_("全备下发目标 DTS Worker IP（可选）"))
    shard_id = serializers.IntegerField(required=False, allow_null=True, help_text=_("TenDBCluster 分片 ID（可选）"))


class MigrateSourceSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("源集群ID"))
    sync_scope = SyncScopeSerializer(required=False, help_text=_("库表同步范围"))
    source_instance_id = serializers.IntegerField(required=False, help_text=_("指定源实例 ID（可选）"))
    source_instance_role = serializers.CharField(required=False, allow_blank=True, help_text=_("指定源实例角色（可选）"))
    source_host = serializers.CharField(required=False, allow_blank=True, help_text=_("指定源地址 ip:port（可选）"))
    myloader = MyloaderSpecSerializer(required=False, help_text=_("该源的 myloader 参数（可选）"))


class MigrateTargetSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("目标集群ID"))
    target_spider = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=_("指定目标 Spider Master 地址 ip:port（可选，仅 TenDBCluster 目标有效）"),
    )

    def validate(self, attrs):
        target_spider = (attrs.get("target_spider") or "").strip()
        if not target_spider:
            attrs["target_spider"] = None
            return attrs

        cluster_id = attrs.get("cluster_id")
        cluster = Cluster.objects.filter(id=cluster_id).first()
        if cluster is None:
            raise serializers.ValidationError({"cluster_id": gettext_runtime("集群 {} 不存在").format(cluster_id)})

        if cluster.cluster_type != ClusterType.TenDBCluster.value:
            raise serializers.ValidationError(
                {"target_spider": gettext_runtime("target_spider 仅适用于 TenDBCluster 目标集群")}
            )

        if IP_PORT_DIVIDER not in target_spider:
            raise serializers.ValidationError({"target_spider": gettext_runtime("target_spider 格式必须为 ip:port")})
        ip, port_str = target_spider.split(IP_PORT_DIVIDER, 1)
        ip, port_str = ip.strip(), port_str.strip()
        try:
            port = int(port_str)
        except ValueError as exc:
            raise serializers.ValidationError(
                {"target_spider": gettext_runtime("target_spider 格式必须为 ip:port")}
            ) from exc

        is_spider_master = cluster.proxyinstance_set.filter(
            machine__ip=ip,
            port=port,
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER,
        ).exists()
        if not is_spider_master:
            raise serializers.ValidationError(
                {"target_spider": gettext_runtime("{}:{} 不是目标集群 {} 的 SPIDER_MASTER").format(ip, port, cluster.id)}
            )

        attrs["target_spider"] = "{}{}{}".format(ip, IP_PORT_DIVIDER, port)
        return attrs


class MigrateOneToOneSerializer(serializers.Serializer):
    source = MigrateSourceSerializer(help_text=_("源集群"))
    target = MigrateTargetSerializer(help_text=_("目标集群"))


class MigrateManyToOneSerializer(serializers.Serializer):
    sources = serializers.ListSerializer(child=MigrateSourceSerializer(), help_text=_("多个源集群"))
    target = MigrateTargetSerializer(help_text=_("目标集群"))


class MigrateOneToManySerializer(serializers.Serializer):
    source = MigrateSourceSerializer(help_text=_("源集群"))
    targets = serializers.ListSerializer(child=MigrateTargetSerializer(), help_text=_("多个目标集群"))


class MigrateSpecSerializer(serializers.Serializer):
    """迁什么：拓扑 + 源/目标。"""

    topology = serializers.ChoiceField(choices=MigrateTopology.get_choices(), help_text=_("迁移拓扑"))
    one_to_one = MigrateOneToOneSerializer(required=False)
    many_to_one = MigrateManyToOneSerializer(required=False)
    one_to_many = MigrateOneToManySerializer(required=False)

    def validate(self, attrs):
        topology = attrs["topology"]
        field_map = {
            MigrateTopology.ONE_TO_ONE.value: "one_to_one",
            MigrateTopology.MANY_TO_ONE.value: "many_to_one",
            MigrateTopology.ONE_TO_MANY.value: "one_to_many",
        }
        field_name = field_map[topology]
        if not attrs.get(field_name):
            raise serializers.ValidationError(gettext_runtime("拓扑 {} 必须填写 migrate.{}").format(topology, field_name))
        return attrs


class DtsDeploySerializer(serializers.Serializer):
    cluster_name = serializers.CharField(required=False, allow_blank=True, help_text=_("DTS 集群名"))
    bk_cloud_id = serializers.IntegerField(required=False, help_text=_("云区域ID"))
    master_hosts = serializers.ListSerializer(child=DtsHostSpecSerializer(), help_text=_("Master 主机列表"))
    worker_hosts = serializers.ListSerializer(child=DtsHostSpecSerializer(), help_text=_("Worker 主机列表"))
    deploy_path = serializers.CharField(required=False, allow_blank=True, help_text=_("部署路径（可选）"))
    master_ha = serializers.BooleanField(default=False, help_text=_("是否 Master HA"))


class DtsResourceSerializer(serializers.Serializer):
    """DTS 集群从哪来、迁完怎么办。"""

    mode = serializers.ChoiceField(
        choices=DtsLifecycleMode.get_choices(),
        help_text=_("DTS 资源模式: use_existing | deploy_ephemeral | deploy_persistent"),
    )
    dts_cluster_id = serializers.IntegerField(
        required=False, help_text=_("已有 DTS 集群 ID（mode=use_existing 时必填，MysqlDtsCluster.id）")
    )
    deploy = DtsDeploySerializer(required=False, help_text=_("部署参数（mode=deploy_* 时必填）"))
    cleanup_after_migrate = serializers.BooleanField(required=False, help_text=_("迁移结束后是否清理临时 DTS（默认：ephemeral=true）"))
    recycle_hosts = serializers.BooleanField(required=False, default=True, help_text=_("清理时是否回收主机"))
    destroy_after_migrate = serializers.BooleanField(required=False, default=False, help_text=_("迁移成功后是否销毁已有 DTS 集群"))

    def validate(self, attrs):
        mode = attrs["mode"]
        if mode == DtsLifecycleMode.USE_EXISTING.value:
            if not attrs.get("dts_cluster_id"):
                raise serializers.ValidationError(gettext_runtime("mode=use_existing 时必须填写 dts_cluster_id"))
        elif mode in (DtsLifecycleMode.DEPLOY_EPHEMERAL.value, DtsLifecycleMode.DEPLOY_PERSISTENT.value):
            if not attrs.get("deploy"):
                raise serializers.ValidationError(gettext_runtime("mode={} 时必须填写 deploy").format(mode))
        if attrs.get("destroy_after_migrate") and mode != DtsLifecycleMode.USE_EXISTING.value:
            raise serializers.ValidationError(gettext_runtime("destroy_after_migrate 仅在 mode=use_existing 时允许为 true"))
        return attrs


class FullLoadSerializer(serializers.Serializer):
    engine = serializers.ChoiceField(
        choices=FullLoadEngine.get_choices(),
        default=FullLoadEngine.BUILTIN.value,
        help_text=_("全量导入引擎: builtin | myloader"),
    )
    myloader = MyloaderSpecSerializer(required=False, help_text=_("engine=myloader 时的参数"))


class TaskSpecSerializer(serializers.Serializer):
    """任务怎么跑。"""

    task_mode = serializers.CharField(required=False, default="all", help_text=_("任务模式: all | full | incremental"))
    full_load = FullLoadSerializer(required=False, help_text=_("全量导入配置"))
    enable_validator = serializers.BooleanField(required=False, default=False, help_text=_("是否开启数据校验"))
    shard_mode = serializers.CharField(required=False, allow_blank=True, default="", help_text=_("分片模式（可选）"))
    on_duplicate = serializers.CharField(required=False, default="replace", help_text=_("冲突策略"))
    meta_schema = serializers.CharField(required=False, default="dm_meta", help_text=_("元数据库名"))
    ignore_checking_items = serializers.ListField(
        child=serializers.CharField(), required=False, default=list, help_text=_("忽略的检查项")
    )
    engine_options = serializers.DictField(
        required=False,
        default=dict,
        help_text=_("引擎透传选项，如 {full_migrate: {}, incr_migrate: {}}"),
    )


class MysqlMigrateBaseDetailSerializer(serializers.Serializer):
    """迁移单据分层入参：dts_resource + migrate + task。"""

    dts_resource = DtsResourceSerializer(help_text=_("DTS 资源（集群来源与生命周期）"))
    migrate = MigrateSpecSerializer(help_text=_("迁移拓扑与源/目标"))
    task = TaskSpecSerializer(required=False, help_text=_("任务运行参数"))

    def validate(self, attrs):
        # 仅做结构校验：此时尚无 ticket.id，不要求最终 task_name（创单后由 patch 回写）
        # 勿写入 attrs：DtsMigratePlan 不可 JSON 序列化，会污染 Ticket.details
        migrate_plan = build_migrate_plan(
            {**attrs, "bk_biz_id": self.context.get("bk_biz_id", 0)},
            require_task_name=False,
        )
        self.context["migrate_plan"] = migrate_plan
        _validate_migrate_grant_cluster_versions(migrate_plan)
        return attrs


_MYSQL_TO_MYSQL_ALLOWED_TYPES = {ClusterType.TenDBHA.value, ClusterType.TenDBSingle.value}


def _collect_migrate_plan_cluster_ids(migrate_plan) -> set[int]:
    cluster_ids: set[int] = set()
    for task_spec in migrate_plan.task_specs:
        for source in task_spec.sources:
            cluster_ids.add(source.cluster_id)
        cluster_ids.add(task_spec.target_cluster_id)
    return cluster_ids


def _validate_migrate_grant_cluster_versions(migrate_plan) -> None:
    """校验迁移授权相关业务集群 major_version 可解析（空/无数字 → 拒单）。"""
    cluster_ids = _collect_migrate_plan_cluster_ids(migrate_plan)
    if not cluster_ids:
        return
    clusters = {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)}
    for cluster_id in sorted(cluster_ids):
        cluster = clusters.get(cluster_id)
        if cluster is None:
            raise serializers.ValidationError(gettext_runtime("集群 {} 不存在").format(cluster_id))
        major_version = cluster.major_version or ""
        if parse_dts_migrate_major_version(major_version) <= 0:
            raise serializers.ValidationError(
                gettext_runtime("集群 {} 的 major_version 无效或为空（当前={!r}），无法创建 DTS 迁移单据").format(cluster_id, major_version)
            )


def _validate_mysql_to_mysql_cluster_types(migrate_plan) -> None:
    """校验 MYSQL_TO_MYSQL_MIGRATE：源/目标仅允许 TenDBHA / TenDBSingle。"""
    cluster_ids = _collect_migrate_plan_cluster_ids(migrate_plan)
    clusters = {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)}
    for cluster_id in cluster_ids:
        cluster = clusters.get(cluster_id)
        if cluster is None:
            raise serializers.ValidationError(gettext_runtime("集群 {} 不存在").format(cluster_id))
        if cluster.cluster_type not in _MYSQL_TO_MYSQL_ALLOWED_TYPES:
            raise serializers.ValidationError(
                gettext_runtime("MYSQL_TO_MYSQL_MIGRATE 仅支持 TenDBHA/TenDBSingle，集群 {} 类型为 {}").format(
                    cluster_id, cluster.cluster_type
                )
            )


class MysqlToMysqlMigrateDetailSerializer(MysqlMigrateBaseDetailSerializer):
    """MySQL 数据迁移（HA/Single 互迁）入参校验。"""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        _validate_mysql_to_mysql_cluster_types(self.context["migrate_plan"])
        return attrs


class MysqlDtsClusterApplyDetailSerializer(serializers.Serializer):
    cluster_name = serializers.CharField(help_text=_("DTS集群名称"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    master_hosts = serializers.ListSerializer(child=DtsHostSpecSerializer())
    worker_hosts = serializers.ListSerializer(child=DtsHostSpecSerializer())
    deploy_path = serializers.CharField(required=False, allow_blank=True)
    master_ha = serializers.BooleanField(default=False)


class RecycleHostsFlagOrListField(serializers.Field):
    """
    DESTROY 单据 recycle_hosts 双形态字段。

    - 建单入参：bool（是否回收主机）
    - patch_ticket_detail 后：覆盖为标准化 host list，供 create_recycle_ticket 消费
    - 详情 to_representation 必须兼容 list，否则 DRF BooleanField 会对 list 做
      ``value in TRUE_VALUES``（set 成员检测）抛出 TypeError: unhashable type: 'list'
    """

    default_error_messages = {"invalid": _("recycle_hosts 必须为布尔值")}

    def __init__(self, **kwargs):
        kwargs.setdefault("default", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, bool):
            return data
        self.fail("invalid")

    def to_representation(self, value):
        return value


class MysqlDtsClusterDestroyDetailSerializer(serializers.Serializer):
    dts_cluster_id = serializers.IntegerField(help_text=_("DTS集群ID"))
    force_destroy = serializers.BooleanField(default=False)
    recycle_hosts = RecycleHostsFlagOrListField(help_text=_("清理时是否回收主机；补齐后为回收主机列表"))
    clean_data_dir = serializers.BooleanField(default=True)


class MysqlDtsClusterApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_dts_cluster_apply_scene

    def format_ticket_data(self):
        if not self.ticket_data.get("deploy_path"):
            self.ticket_data["deploy_path"] = get_default_deploy_path(self.ticket_data["cluster_name"])


@builders.BuilderFactory.register(TicketType.MYSQL_DTS_CLUSTER_APPLY, is_apply=True, cluster_type=ClusterType.MySQLDTS)
class MysqlDtsClusterApplyFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlDtsClusterApplyDetailSerializer
    inner_flow_builder = MysqlDtsClusterApplyFlowParamBuilder
    inner_flow_name = _("MySQL DTS 集群部署")


class MysqlDtsClusterDestroyFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_dts_cluster_destroy_scene


class MysqlDtsClusterReinstallDetailSerializer(serializers.Serializer):
    dts_cluster_id = serializers.IntegerField(help_text=_("DTS集群ID"))
    dts_pkg_id = serializers.IntegerField(required=False, allow_null=True, help_text=_("指定介质包ID"))
    force_reinstall = serializers.BooleanField(default=False, help_text=_("有运行中任务时是否强制重装"))


class MysqlDtsClusterReinstallFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_dts_cluster_reinstall_scene


@builders.BuilderFactory.register(TicketType.MYSQL_DTS_CLUSTER_REINSTALL)
class MysqlDtsClusterReinstallFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlDtsClusterReinstallDetailSerializer
    inner_flow_builder = MysqlDtsClusterReinstallFlowParamBuilder
    inner_flow_name = _("MySQL DTS 集群重装")


@builders.BuilderFactory.register(TicketType.MYSQL_DTS_CLUSTER_DESTROY, is_recycle=True)
class MysqlDtsClusterDestroyFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlDtsClusterDestroyDetailSerializer
    inner_flow_builder = MysqlDtsClusterDestroyFlowParamBuilder
    inner_flow_name = _("MySQL DTS 集群销毁")

    def patch_recycle_dts_host_details(self):
        """
        从 MysqlDtsCluster 节点补齐标准化回收主机列表。

        注意：建单入参 `recycle_hosts` 为布尔开关（默认 True）；patch 后会覆盖为 list，
        供成功钩子 `create_recycle_ticket` 消费。显式 False 时写空列表以跳过关联单。
        """
        details = self.ticket.details
        should_recycle = details.get("recycle_hosts", True)
        if should_recycle is False:
            details["recycle_hosts"] = []
            return

        dts_cluster_id = details.get("dts_cluster_id")
        dts_cluster = MysqlDtsCluster.objects.filter(id=dts_cluster_id).first()
        if not dts_cluster:
            logger.warning(gettext_runtime("DTS 销毁补齐回收主机失败: 集群 {} 不存在").format(dts_cluster_id))
            details["recycle_hosts"] = []
            return

        # master/worker 同机部署时按 (ip, bk_cloud_id) 去重
        host_keys = []
        seen = set()
        for node in list(dts_cluster.master_nodes or []) + list(dts_cluster.worker_nodes or []):
            ip = node.get("ip")
            if not ip:
                continue
            bk_cloud_id = node.get("bk_cloud_id", dts_cluster.bk_cloud_id)
            key = (ip, bk_cloud_id)
            if key in seen:
                continue
            seen.add(key)
            host_keys.append(key)

        recycle_hosts = []
        for ip, bk_cloud_id in host_keys:
            machine = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
            if not machine or not machine.bk_host_id:
                logger.warning(gettext_runtime("DTS 销毁回收跳过主机 {}:{}，未找到 Machine 或 bk_host_id").format(bk_cloud_id, ip))
                continue
            recycle_hosts.append({"bk_host_id": machine.bk_host_id})

        if not recycle_hosts:
            details["recycle_hosts"] = []
            return

        details["recycle_hosts"] = ResourceHandler.standardized_resource_host(recycle_hosts)

    def patch_ticket_detail(self):
        self.patch_recycle_dts_host_details()
        super().patch_ticket_detail()


def _patch_migrate_task_names(ticket) -> None:
    """Ticket 已创建后，按拓扑自动生成 task_name 并写回 details.migrate。"""
    if not getattr(ticket, "id", None):
        return
    patch_migrate_task_names_into_details(ticket.details, ticket.id)


def _has_related_destroy_for_cluster(ticket, dts_cluster_id) -> bool:
    """父单据是否已关联同 dts_cluster_id 的 MYSQL_DTS_CLUSTER_DESTROY。"""
    flow_set = getattr(ticket, "flow_set", None)
    if flow_set is None:
        return False
    try:
        related_ids = [
            flow.details.get("related_ticket")
            for flow in flow_set.filter(flow_type=FlowType.DELIVERY.value)
            if (flow.details or {}).get("related_ticket")
        ]
        if not related_ids:
            return False
        return Ticket.objects.filter(
            id__in=related_ids,
            ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY,
            details__dts_cluster_id=dts_cluster_id,
        ).exists()
    except Exception:
        # mock / 非 ORM 场景下幂等探测失败时不阻断创单
        return False


def _maybe_create_destroy_after_migrate(ticket) -> None:
    """
    迁移单据成功后，按需串联 MYSQL_DTS_CLUSTER_DESTROY。

    仅 use_existing + destroy_after_migrate=true 时生效；创单异常只记日志，不回滚迁移成功态。
    """
    try:
        dts_resource = (ticket.details or {}).get("dts_resource") or {}
        if dts_resource.get("mode") != DtsLifecycleMode.USE_EXISTING.value:
            return
        if not dts_resource.get("destroy_after_migrate"):
            return
        dts_cluster_id = dts_resource.get("dts_cluster_id")
        if not dts_cluster_id:
            return
        if _has_related_destroy_for_cluster(ticket, dts_cluster_id):
            logger.info(gettext_runtime("迁移单据 {} 已关联 DTS 集群 {} 的销毁单，跳过重复创建").format(ticket.id, dts_cluster_id))
            return

        destroy_ticket = Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY,
            creator=ticket.creator,
            bk_biz_id=ticket.bk_biz_id,
            remark=gettext_runtime("迁移单据{}成功后自动销毁 DTS").format(ticket.id),
            details={
                "dts_cluster_id": dts_cluster_id,
                "recycle_hosts": dts_resource.get("recycle_hosts", True),
            },
            auto_execute=True,
        )
        ticket.add_related_ticket(destroy_ticket, done=True)
    except Exception as e:
        logger.error(gettext_runtime("迁移单据 {} 串联销毁 DTS 失败: {}").format(getattr(ticket, "id", None), str(e)))


class MysqlToMysqlMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_to_mysql_migrate_scene

    def format_ticket_data(self):
        self.ticket_data["ticket_id"] = self.ticket.id
        self.ticket_data["migrate_type"] = "mysql_to_mysql"
        # migrate_plan 由 flow 内 build_migrate_plan(self.data) 构建，勿写入 ticket_data（不可 JSON 序列化）

    def post_callback(self):
        flow = self.ticket.current_flow()
        if flow.status != TicketFlowStatus.SUCCEEDED:
            return
        _maybe_create_destroy_after_migrate(self.ticket)


@builders.BuilderFactory.register(TicketType.MYSQL_TO_MYSQL_MIGRATE)
class MysqlToMysqlMigrateFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlToMysqlMigrateDetailSerializer
    inner_flow_builder = MysqlToMysqlMigrateFlowParamBuilder
    inner_flow_name = _("MySQL 数据迁移")

    def patch_ticket_detail(self):
        _patch_migrate_task_names(self.ticket)
        super().patch_ticket_detail()


class MysqlHaToClusterMigrateFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_to_cluster_migrate_scene

    def format_ticket_data(self):
        self.ticket_data["ticket_id"] = self.ticket.id
        self.ticket_data["migrate_type"] = "ha_to_cluster"
        # migrate_plan 由 flow 内 build_migrate_plan(self.data) 构建，勿写入 ticket_data（不可 JSON 序列化）

    def post_callback(self):
        flow = self.ticket.current_flow()
        if flow.status != TicketFlowStatus.SUCCEEDED:
            return
        _maybe_create_destroy_after_migrate(self.ticket)


@builders.BuilderFactory.register(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE)
class MysqlHaToClusterMigrateFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlMigrateBaseDetailSerializer
    inner_flow_builder = MysqlHaToClusterMigrateFlowParamBuilder
    inner_flow_name = _("MySQL HA到Cluster数据迁移")

    def patch_ticket_detail(self):
        _patch_migrate_task_names(self.ticket)
        super().patch_ticket_detail()
