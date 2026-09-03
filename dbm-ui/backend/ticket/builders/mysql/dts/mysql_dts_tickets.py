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
from backend.db_meta.models import Cluster, Machine, MysqlDtsCluster, Spec
from backend.db_meta.models.mysql_dts import MysqlDtsInfo
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
from backend.flow.utils.mysql.dts.migrate_helper import resolve_destroy_cluster_ids
from backend.flow.utils.mysql.dts.migrate_plan import (
    TICKET_LIFECYCLE_FIELDS,
    build_migrate_plan,
    build_migrate_plans,
    infer_dts_resource_intent,
    infer_rename_migrate_type_from_plan,
    is_real_rename_route,
    patch_deploy_cluster_names_into_details,
    resolve_ticket_destroy_policy,
    resolve_ticket_lifecycle,
)
from backend.flow.utils.mysql.dts.sync_scope_overlap import landing_objects, objects_overlap, source_objects
from backend.flow.utils.mysql.dts.task_name import patch_migrate_task_names_into_details
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import FlowType, TicketType
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
    task_name = serializers.CharField(required=False, allow_blank=True, help_text=_("自动生成的迁移任务名"))


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
    # 资源池模式(master/worker 由资源申请回填)下可不传，手动录入模式需传
    master_hosts = serializers.ListSerializer(
        child=DtsHostSpecSerializer(), required=False, help_text=_("Master 主机列表（资源池模式无需传入）")
    )
    worker_hosts = serializers.ListSerializer(
        child=DtsHostSpecSerializer(), required=False, help_text=_("Worker 主机列表（资源池模式无需传入）")
    )
    deploy_path = serializers.CharField(required=False, allow_blank=True, help_text=_("部署路径（可选）"))
    master_ha = serializers.BooleanField(default=False, help_text=_("是否 Master HA"))


class DtsResourceBaseSerializer(serializers.Serializer):
    """DTS 集群从哪来（不含整单生命周期）。"""

    mode = serializers.ChoiceField(
        choices=DtsLifecycleMode.get_choices(),
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text=_("可选，默认不传；按 dts_cluster_id / deploy 推断 use_existing | deploy"),
    )
    dts_cluster_id = serializers.IntegerField(required=False, help_text=_("已有 DTS 集群 ID（复用时必填，MysqlDtsCluster.id）"))
    deploy = DtsDeploySerializer(required=False, help_text=_("本单现场部署参数（与 dts_cluster_id 二选一）"))

    def validate(self, attrs):
        try:
            infer_dts_resource_intent(attrs)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))
        return attrs


class DtsResourceSerializer(DtsResourceBaseSerializer):
    """单行 dts_resource：集群来源 + 生命周期。"""

    cleanup_after_migrate = serializers.BooleanField(
        required=False, help_text=_("迁移结束后是否清理 DTS（deploy 默认 true，复用默认 false）")
    )
    recycle_hosts = serializers.BooleanField(required=False, default=True, help_text=_("清理时是否回收主机"))
    destroy_after_migrate = serializers.BooleanField(
        required=False, default=True, help_text=_("迁移成功后是否串联销毁单据（默认 true；复用或本单部署均可）")
    )


class MysqlMigrateRowResourceSerializer(DtsResourceBaseSerializer):
    """多行 infos[].dts_resource：只允许集群来源，生命周期写在单据顶层。"""


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
    on_duplicate = serializers.CharField(required=False, default="error", help_text=_("冲突策略"))
    meta_schema = serializers.CharField(required=False, default="dm_meta", help_text=_("元数据库名"))
    ignore_checking_items = serializers.ListField(
        child=serializers.CharField(), required=False, default=list, help_text=_("忽略的检查项")
    )
    engine_options = serializers.DictField(
        required=False,
        default=dict,
        help_text=_("引擎透传选项，如 {full_migrate: {}, incr_migrate: {}}"),
    )


class DtsResourceSpecRoleSerializer(serializers.Serializer):
    """资源池申请规格（按角色 master/worker）：spec_id + 数量 + 标签，不依赖城市匹配。

    申请参数透传给资源池（flow_manager.resource.ResourceApplyFlow.fetch_apply_params），
    标签用于从资源池精确匹配目标机器；位置匹配 location_spec 可选，联调按标签匹配时无需填城市。
    """

    spec_id = serializers.IntegerField(help_text=_("规格ID（资源池机型规格，必填）"))
    count = serializers.IntegerField(min_value=1, help_text=_("申请数量（必填）"))
    labels = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text=_("资源标签：从资源池精确匹配目标机器，如 ['dts-pool']（联调按标签匹配时无需传城市）"),
    )
    label_names = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text=_("资源标签名称"),
    )
    location_spec = serializers.DictField(
        required=False,
        default=dict,
        help_text=_("位置匹配参数（可选；联调按标签匹配机器时无需传城市，留空即可）"),
    )


class MysqlMigrateRowSerializer(serializers.Serializer):
    """多行 infos 中的一行：资源来源 + 拓扑；生命周期写在单据顶层。"""

    dts_resource = MysqlMigrateRowResourceSerializer(help_text=_("DTS 资源（集群来源）"))
    migrate = MigrateSpecSerializer(help_text=_("迁移拓扑与源/目标"))
    task = TaskSpecSerializer(required=False, help_text=_("任务运行参数"))
    resource_spec = serializers.DictField(
        child=DtsResourceSpecRoleSerializer(),
        required=False,
        default=dict,
        help_text=_("行内资源规格（deploy 部署时按角色 master/worker 申请；多行共用一套 deploy 时需一致）"),
    )


class MysqlMigrateBaseDetailSerializer(serializers.Serializer):
    """迁移单据分层入参：dts_resource + migrate + task，或多行 infos。"""

    dts_resource = DtsResourceSerializer(required=False, help_text=_("DTS 资源（集群来源与生命周期）"))
    migrate = MigrateSpecSerializer(required=False, help_text=_("迁移拓扑与源/目标"))
    task = TaskSpecSerializer(required=False, help_text=_("任务运行参数"))
    infos = MysqlMigrateRowSerializer(many=True, required=False, help_text=_("多行独立 one_to_one"))
    destroy_after_migrate = serializers.BooleanField(
        required=False,
        help_text=_("迁移成功后是否串联销毁单据（多行 infos 时整单生效，默认 true；单行请写在 dts_resource）"),
    )
    recycle_hosts = serializers.BooleanField(
        required=False,
        help_text=_("销毁时是否回收主机（多行 infos 时整单生效，默认 true；单行请写在 dts_resource）"),
    )
    cleanup_after_migrate = serializers.BooleanField(
        required=False,
        help_text=_("迁移结束后是否在本流程清理 DTS（多行 infos 时整单生效，默认 false；单行请写在 dts_resource）"),
    )
    nodes = serializers.DictField(
        required=False,
        help_text=_("资源申请主机明细（按角色 master/worker 分组，由资源申请回写；占位结构 {master: [], worker: []}）"),
    )
    specs = serializers.DictField(
        required=False,
        help_text=_("资源申请规格（按角色 master/worker 分组，由资源申请回写；占位结构 {master: [], worker: []}）"),
    )
    clusters = serializers.DictField(
        required=False,
        help_text=_("集群信息"),
    )

    def validate(self, attrs):
        # 仅做结构校验：此时尚无 ticket.id，不要求最终 task_name（创单后由 patch 回写）
        # 勿写入 attrs：DtsMigratePlan 不可 JSON 序列化，会污染 Ticket.details
        infos = attrs.get("infos") or []
        if infos:
            if attrs.get("dts_resource") or attrs.get("migrate"):
                raise serializers.ValidationError(gettext_runtime("有 infos 时不要再传顶层 migrate / dts_resource"))
            _validate_infos_one_to_one(infos)
            _validate_infos_row_lifecycle_forbidden(_raw_ticket_details(self, attrs))
            _validate_infos_deploy_hosts_unique(infos)
            attrs.update(resolve_ticket_lifecycle(attrs))
            plans = build_migrate_plans(
                {**attrs, "bk_biz_id": self.context.get("bk_biz_id", 0)},
                require_task_name=False,
            )
        else:
            if not attrs.get("migrate"):
                raise serializers.ValidationError(gettext_runtime("必须提供migrate，或多行 infos"))
            _validate_single_row_top_lifecycle_forbidden(_raw_ticket_details(self, attrs))
            plans = [
                build_migrate_plan(
                    {**attrs, "bk_biz_id": self.context.get("bk_biz_id", 0)},
                    require_task_name=False,
                )
            ]
        self.context["migrate_plans"] = plans
        self.context["migrate_plan"] = plans[0]
        for plan in plans:
            _validate_migrate_grant_cluster_versions(plan)
        has_infos = bool(infos)
        _validate_sync_scope_nonempty(plans, has_infos=has_infos)
        _validate_src_ne_dst(plans, has_infos=has_infos)
        if has_infos:
            _validate_infos_object_overlap(plans)
        _validate_resource_pool_deploy(attrs)
        return attrs


_DTS_DEPLOY_ROLES = ("master", "worker")


def _iter_dts_deploys(attrs: dict) -> list:
    """收集单据中的 deploy（单行 dts_resource.deploy 或 infos[].dts_resource.deploy）。"""
    deploys = []
    infos = attrs.get("infos") or []
    if infos:
        for row in infos:
            deploy = (row.get("dts_resource") or {}).get("deploy")
            if deploy:
                deploys.append(deploy)
    else:
        deploy = (attrs.get("dts_resource") or {}).get("deploy")
        if deploy:
            deploys.append(deploy)
    return deploys


def _resolve_resource_spec(details: dict) -> dict:
    """取整单 resource_spec：仅从 infos 行内取（多行需一致，共用一套 deploy 集群）。"""
    specs = []
    for row in details.get("infos") or []:
        rs = (row or {}).get("resource_spec")
        if rs:
            specs.append(rs)
    if not specs:
        return {}
    first = specs[0]
    for rs in specs[1:]:
        if rs != first:
            raise serializers.ValidationError(gettext_runtime("多行 infos 的 resource_spec 需一致（共用一套 deploy 集群）"))
    return first


def _resolve_specs_map(details: dict) -> dict:
    """将 resource_spec 引用的 spec_id 批量映射为规格详情，供详情接口/流程消费。

    返回 {spec_id: Spec.get_spec_info()}；无资源池申请规格时返回空 dict。
    """
    resource_spec = _resolve_resource_spec(details)
    spec_ids = []
    for role_spec in resource_spec.values():
        if not isinstance(role_spec, dict):
            continue
        spec_id = role_spec.get("spec_id")
        if spec_id:
            spec_ids.append(int(spec_id))
    spec_ids = sorted(set(spec_ids))
    if not spec_ids:
        return {}
    return {spec.spec_id: spec.get_spec_info() for spec in Spec.objects.filter(spec_id__in=spec_ids)}


def _validate_resource_pool_deploy(attrs: dict) -> None:
    """校验 deploy 本单部署：master/worker 主机由资源申请回填，不可手动传入。

    生效：存在 deploy（顶层 dts_resource.deploy 或 infos[].dts_resource.deploy）。
    合法反例：deploy.master_hosts/worker_hosts 为空，由 resource_spec 描述申请规格。
    """
    resource_spec = _resolve_resource_spec(attrs)
    deploys = _iter_dts_deploys(attrs)
    for deploy in deploys:
        for role in _DTS_DEPLOY_ROLES:
            if deploy.get(f"{role}_hosts"):
                raise serializers.ValidationError(
                    gettext_runtime("资源池模式下 {} 主机由资源申请回填，请勿在 deploy.{}_hosts 中传入").format(role, role)
                )
        for role in _DTS_DEPLOY_ROLES:
            if not resource_spec.get(role):
                raise serializers.ValidationError(
                    gettext_runtime("资源池模式下 deploy 部署必须提供 resource_spec.{} 申请规格").format(role)
                )


_MYSQL_TO_MYSQL_ALLOWED_TYPES = {ClusterType.TenDBHA.value, ClusterType.TenDBSingle.value}


def _raw_ticket_details(serializer, attrs) -> dict:
    """取原始 details，用于检查 DRF 会丢弃的行内生命周期字段。

    建单走 TicketDetailsSerializer 时只调 exact.validate(attrs)，实例没有 initial_data，
    需回退 request.data.details；直连 Serializer(data=) 时仍用 initial_data。
    """
    raw = getattr(serializer, "initial_data", None)
    if isinstance(raw, dict):
        return raw
    request = (serializer.context or {}).get("request")
    if request is not None:
        details = (getattr(request, "data", None) or {}).get("details")
        if isinstance(details, dict):
            return details
    return attrs if isinstance(attrs, dict) else {}


def _validate_infos_row_lifecycle_forbidden(initial_data) -> None:
    """拦 infos 行内 / 行内 dts_resource 再写生命周期字段。
    生效：仅 infos[]。合法反例：destroy_after_migrate 等写在单据顶层。
    """
    if not isinstance(initial_data, dict):
        return
    for idx, row in enumerate(initial_data.get("infos") or []):
        if not isinstance(row, dict):
            continue
        leaked = [field for field in TICKET_LIFECYCLE_FIELDS if field in row]
        resource = row.get("dts_resource") or {}
        if isinstance(resource, dict):
            leaked.extend(field for field in TICKET_LIFECYCLE_FIELDS if field in resource)
        if leaked:
            raise serializers.ValidationError(
                gettext_runtime("infos[{}] 的 {} 请写在单据顶层，不要放在行内 dts_resource").format(
                    idx, " / ".join(dict.fromkeys(leaked))
                )
            )


def _validate_single_row_top_lifecycle_forbidden(initial_data) -> None:
    """拦无 infos 时把生命周期写在单据顶层。
    生效：仅单行 migrate。合法反例：字段写在 dts_resource。
    """
    if not isinstance(initial_data, dict):
        return
    if initial_data.get("infos"):
        return
    leaked = [field for field in TICKET_LIFECYCLE_FIELDS if field in initial_data]
    if leaked:
        raise serializers.ValidationError(
            gettext_runtime("无 infos 时 {} 请写在 dts_resource，不要写在单据顶层").format(" / ".join(dict.fromkeys(leaked)))
        )


def _validate_infos_one_to_one(infos: list) -> None:
    """拦 infos 行拓扑不是 one_to_one。生效：仅 infos[]。合法反例：每行 topology=one_to_one。"""
    for idx, row in enumerate(infos):
        topology = (row.get("migrate") or {}).get("topology")
        if topology != MigrateTopology.ONE_TO_ONE.value:
            raise serializers.ValidationError(
                gettext_runtime("infos[{}] 仅支持 one_to_one 拓扑，实际为 {}").format(idx, topology)
            )


def _collect_deploy_host_keys(deploy: dict | None) -> list[tuple]:
    if not deploy:
        return []
    keys = []
    for host in list(deploy.get("master_hosts") or []) + list(deploy.get("worker_hosts") or []):
        ip = host.get("ip")
        if not ip:
            continue
        keys.append((ip, int(host.get("bk_cloud_id") or 0)))
    return keys


def _validate_infos_deploy_hosts_unique(infos: list) -> None:
    """拦跨行 deploy 机器交叉。生效：仅 infos[]。合法反例：同行 master/worker 同机；不同行用不同 IP。"""
    seen: dict[tuple, int] = {}
    for idx, row in enumerate(infos):
        deploy = (row.get("dts_resource") or {}).get("deploy")
        for key in set(_collect_deploy_host_keys(deploy)):
            if key in seen and seen[key] != idx:
                raise serializers.ValidationError(
                    gettext_runtime("多行 deploy 机器交叉：{} 同时出现在 infos[{}] 与 infos[{}]").format(key[0], seen[key], idx)
                )
            seen[key] = idx


def _collect_migrate_plan_cluster_ids(migrate_plan) -> set[int]:
    cluster_ids: set[int] = set()
    for task_spec in migrate_plan.task_specs:
        for source in task_spec.sources:
            cluster_ids.add(source.cluster_id)
        cluster_ids.add(task_spec.target_cluster_id)
    return cluster_ids


def _row_label(idx: int, has_infos: bool) -> str:
    return "infos[{}]".format(idx) if has_infos else "migrate"


def _iter_plan_sources(plans):
    for idx, plan in enumerate(plans):
        for spec in plan.task_specs:
            for source in spec.sources:
                yield idx, spec, source


def _validate_sync_scope_nonempty(plans, *, has_infos: bool) -> None:
    """拦空同步范围（空规则在引擎侧等于全库，产品不允许靠空范围表达全量）。
    生效：每行，三种迁移单。合法反例：do_dbs 列出库名，或 do_dbs=['*'] 表示整实例。
    """
    for idx, _spec, source in _iter_plan_sources(plans):
        if source_objects(source.sync_scope):
            continue
        raise serializers.ValidationError(
            gettext_runtime("{} 同步范围为空，请填写 do_dbs / table_routes（整实例全量请传 do_dbs=['*']）").format(
                _row_label(idx, has_infos)
            )
        )


def _validate_src_ne_dst(plans, *, has_infos: bool) -> None:
    """拦源集群等于目标集群（自己迁自己）。生效：每行，普通迁移与重命名。合法反例：源 ID 与目标 ID 不同。"""
    for idx, spec, source in _iter_plan_sources(plans):
        if source.cluster_id != spec.target_cluster_id:
            continue
        raise serializers.ValidationError(
            gettext_runtime("{} 源集群与目标集群不能相同（当前均为 {}）").format(_row_label(idx, has_infos), source.cluster_id)
        )


def _validate_infos_object_overlap(plans) -> None:
    """拦 infos 中同一源+同一目标的库表对象重叠。
    生效：仅 infos[] 跨行。合法反例：同源同目标但库不同；同源不同目标同库。
    """
    buckets: dict[tuple[int, int], list[tuple[int, set]]] = {}
    for idx, spec, source in _iter_plan_sources(plans):
        key = (source.cluster_id, spec.target_cluster_id)
        buckets.setdefault(key, []).append((idx, source_objects(source.sync_scope)))
    for (src_id, dst_id), items in buckets.items():
        for left_i, left_objs in items:
            for right_i, right_objs in items:
                if right_i <= left_i:
                    continue
                if objects_overlap(left_objs, right_objs):
                    raise serializers.ValidationError(
                        gettext_runtime("infos[{}] 与 infos[{}] 在源集群 {} 到目标集群 {} 上迁移对象重叠").format(
                            left_i, right_i, src_id, dst_id
                        )
                    )


def _validate_infos_rename_dest_landing(plans) -> None:
    """拦重命名 infos 不同行落到同一目标库表。
    生效：仅 MYSQL_RENAME_MIGRATE 的 infos[]。合法反例：目标集群不同，或落地库表不同。
    """
    by_dst: dict[int, list[tuple[int, set]]] = {}
    for idx, spec, source in _iter_plan_sources(plans):
        by_dst.setdefault(spec.target_cluster_id, []).append((idx, landing_objects(source.sync_scope)))
    for dst_id, items in by_dst.items():
        for left_i, left_objs in items:
            for right_i, right_objs in items:
                if right_i <= left_i:
                    continue
                if objects_overlap(left_objs, right_objs):
                    raise serializers.ValidationError(
                        gettext_runtime("infos[{}] 与 infos[{}] 重命名后落到目标集群 {} 的同一库表").format(left_i, right_i, dst_id)
                    )


def _validate_migrate_grant_cluster_versions(migrate_plan) -> None:
    """拦业务集群 major_version 无法解析。生效：每行。合法反例：集群存在且版本含数字。"""
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
        for plan in self.context.get("migrate_plans") or [self.context["migrate_plan"]]:
            _validate_mysql_to_mysql_cluster_types(plan)
        return attrs


def _validate_rename_one_to_one(attrs: dict) -> None:
    """拦重命名单据拓扑不是 one_to_one。生效：重命名单行与 infos[]。合法反例：topology=one_to_one。"""
    infos = attrs.get("infos") or []
    if infos:
        _validate_infos_one_to_one(infos)
        return
    topology = (attrs.get("migrate") or {}).get("topology")
    if topology != MigrateTopology.ONE_TO_ONE.value:
        raise serializers.ValidationError(gettext_runtime("重命名迁移仅支持 one_to_one 拓扑，实际为 {}").format(topology))


def _validate_rename_routes(plan) -> None:
    """拦重命名缺少真实改名路由。生效：重命名每行。合法反例：table_routes 的 target 与源不同。"""
    for spec in plan.task_specs:
        for source in spec.sources:
            routes = source.sync_scope.table_routes or []
            if not routes:
                raise serializers.ValidationError(
                    gettext_runtime("重命名迁移必须提供 source.sync_scope.table_routes，不能只传 do_dbs")
                )
            for route in routes:
                if not is_real_rename_route(route):
                    raise serializers.ValidationError(
                        gettext_runtime("重命名迁移的 table_routes 必须填写与源不同的 target_db / target_table")
                    )


def _collect_plans_clusters(plans) -> dict:
    cluster_ids: set[int] = set()
    for plan in plans:
        cluster_ids.update(_collect_migrate_plan_cluster_ids(plan))
    if not cluster_ids:
        return {}
    return {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)}


def _write_back_rename_migrate_types(attrs: dict, plans, clusters: dict) -> None:
    infos = attrs.get("infos") or []
    if infos:
        for idx, plan in enumerate(plans):
            try:
                infos[idx]["migrate_type"] = infer_rename_migrate_type_from_plan(plan, clusters)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc))
        return
    try:
        attrs["migrate_type"] = infer_rename_migrate_type_from_plan(plans[0], clusters)
    except ValueError as exc:
        raise serializers.ValidationError(str(exc))


class MysqlRenameMigrateDetailSerializer(MysqlMigrateBaseDetailSerializer):
    """MySQL 重命名迁移：one_to_one + 强制改名路由，按行推断 migrate_type。"""

    def validate(self, attrs):
        attrs = super().validate(attrs)
        _validate_rename_one_to_one(attrs)
        plans = self.context.get("migrate_plans") or [self.context["migrate_plan"]]
        for plan in plans:
            _validate_rename_routes(plan)
        if attrs.get("infos"):
            _validate_infos_rename_dest_landing(plans)
        clusters = _collect_plans_clusters(plans)
        _write_back_rename_migrate_types(attrs, plans, clusters)
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
    dts_cluster_id = serializers.IntegerField(required=False, help_text=_("DTS集群ID（单集群销毁）"))
    dts_cluster_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text=_("多个 DTS 集群 ID（一张销毁单清多集群，与 dts_cluster_id 二选一）"),
    )
    force_destroy = serializers.BooleanField(default=False)
    recycle_hosts = RecycleHostsFlagOrListField(help_text=_("清理时是否回收主机；补齐后为回收主机列表"))
    clean_data_dir = serializers.BooleanField(default=True)

    def validate(self, attrs):
        ids = resolve_destroy_cluster_ids(attrs)
        if not ids:
            raise serializers.ValidationError(gettext_runtime("必须提供 dts_cluster_id 或 dts_cluster_ids"))
        if attrs.get("dts_cluster_id") and attrs.get("dts_cluster_ids"):
            raise serializers.ValidationError(gettext_runtime("dts_cluster_id 与 dts_cluster_ids 不能同时传入"))
        return attrs


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
        # 派生的 RECYCLE_OLD_HOST 属于 mysql 分组，但必须保留 DTS 子类型和部署目录，
        # 供清机 Flow 选择 DTS 专用脚本，禁止误用 MySQL 通用清机脚本。
        details["cluster_type"] = ClusterType.MySQLDTS.value
        should_recycle = details.get("recycle_hosts", True)
        if should_recycle is False:
            details["recycle_hosts"] = []
            return

        cluster_ids = resolve_destroy_cluster_ids(details)
        dts_clusters = list(MysqlDtsCluster.objects.filter(id__in=cluster_ids))
        if not dts_clusters:
            logger.warning(gettext_runtime("DTS 销毁补齐回收主机失败: 集群 {} 不存在").format(cluster_ids))
            details["recycle_hosts"] = []
            return

        if len(dts_clusters) == 1 and dts_clusters[0].deploy_path:
            details["dts_deploy_path"] = dts_clusters[0].deploy_path

        host_keys = []
        seen = set()
        path_by_host_id: dict[int, str] = {}
        recycle_hosts = []
        for dts_cluster in dts_clusters:
            for node in list(dts_cluster.master_nodes or []) + list(dts_cluster.worker_nodes or []):
                ip = node.get("ip")
                if not ip:
                    continue
                bk_cloud_id = node.get("bk_cloud_id", dts_cluster.bk_cloud_id)
                key = (ip, bk_cloud_id)
                if key in seen:
                    continue
                seen.add(key)
                host_keys.append((key, dts_cluster.deploy_path))

        for (ip, bk_cloud_id), deploy_path in host_keys:
            machine = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
            if not machine or not machine.bk_host_id:
                logger.warning(gettext_runtime("DTS 销毁回收跳过主机 {}:{}，未找到 Machine 或 bk_host_id").format(bk_cloud_id, ip))
                continue
            recycle_hosts.append({"bk_host_id": machine.bk_host_id})
            if deploy_path:
                path_by_host_id[int(machine.bk_host_id)] = deploy_path

        if not recycle_hosts:
            details["recycle_hosts"] = []
            return

        details["recycle_hosts"] = ResourceHandler.standardized_resource_host(recycle_hosts)
        paths = {p for p in path_by_host_id.values() if p}
        if len(paths) > 1:
            details["dts_deploy_path_by_host"] = {str(hid): path for hid, path in path_by_host_id.items()}
        elif paths:
            details["dts_deploy_path"] = next(iter(paths))

    def patch_ticket_detail(self):
        self.patch_recycle_dts_host_details()
        super().patch_ticket_detail()


def _patch_migrate_task_names(ticket) -> None:
    """Ticket 已创建后，按拓扑自动生成 task_name 并写回 details.migrate。"""
    if not getattr(ticket, "id", None):
        return
    patch_migrate_task_names_into_details(ticket.details, ticket.id)


def _patch_migrate_deploy_cluster_names(ticket) -> None:
    """多行 infos 本单部署：cluster_name 追加随机后缀并写回，避免同源/同目标撞名。"""
    if not getattr(ticket, "id", None):
        return
    patch_deploy_cluster_names_into_details(ticket.details, ticket.id)


def _related_destroy_ticket_ids(ticket) -> list[int]:
    flow_set = getattr(ticket, "flow_set", None)
    if flow_set is None:
        return []
    try:
        return [
            flow.details.get("related_ticket")
            for flow in flow_set.filter(flow_type=FlowType.DELIVERY.value)
            if (flow.details or {}).get("related_ticket")
        ]
    except Exception:
        return []


def _has_related_destroy_for_clusters(ticket, cluster_ids: list[int]) -> bool:
    """父单据是否已关联覆盖相同 ID 集合的 MYSQL_DTS_CLUSTER_DESTROY。"""
    related_ids = _related_destroy_ticket_ids(ticket)
    if not related_ids:
        return False
    wanted = sorted(set(int(cid) for cid in cluster_ids if cid))
    if not wanted:
        return False
    try:
        for destroy_ticket in Ticket.objects.filter(
            id__in=related_ids,
            ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY,
        ):
            existing = sorted(resolve_destroy_cluster_ids(destroy_ticket.details or {}))
            if existing == wanted:
                return True
        return False
    except Exception:
        return False


def _iter_ticket_dts_resources(details: dict) -> list[dict]:
    infos = details.get("infos") or []
    if infos:
        return [row.get("dts_resource") or {} for row in infos]
    resource = details.get("dts_resource") or {}
    return [resource] if resource else []


def _collect_destroy_dts_cluster_ids(ticket) -> list[int]:
    """收集本单应销毁的全部 DTS 集群 ID。"""
    details = ticket.details or {}
    if not resolve_ticket_destroy_policy(details)["destroy_after_migrate"]:
        return []
    resources = _iter_ticket_dts_resources(details)
    if not resources:
        return []

    ids: list[int] = []
    seen: set[int] = set()

    def _add(cid):
        if not cid:
            return
        cid = int(cid)
        if cid not in seen:
            seen.add(cid)
            ids.append(cid)

    need_info_lookup = False
    for resource in resources:
        try:
            intent = infer_dts_resource_intent(resource)
        except ValueError:
            continue
        if intent.dts_cluster_id:
            _add(intent.dts_cluster_id)
        else:
            need_info_lookup = True

    if need_info_lookup:
        try:
            for cid in MysqlDtsInfo.objects.filter(ticket_id=ticket.id).values_list("dts_cluster_id", flat=True):
                _add(cid)
        except Exception:
            logger.exception(
                gettext_runtime("收集销毁 DTS 集群 ID 失败，中止本次销毁创建 ticket_id={}").format(getattr(ticket, "id", None))
            )
            return []
    return ids


DTS_MIGRATE_TICKET_TYPES = frozenset(
    {
        TicketType.MYSQL_DTS_DATA_MIGRATE,
        TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE,
        TicketType.MYSQL_DTS_DATA_MIGRATE_RENAME,
    }
)


def _maybe_create_destroy_after_migrate(ticket) -> None:
    """
    迁移单据整单 SUCCEEDED 后，按需串联 MYSQL_DTS_CLUSTER_DESTROY。

    由 ticket_status_trigger 调用，不在 inner post_callback 里挂单，避免校验 PENDING 时再插
    SUCCEEDED 销毁节点卡住 run_next_flow。destroy_after_migrate=true 时生效；多行只建一张。
    创单异常只记日志，不回滚迁移成功态。
    """
    try:
        details = ticket.details or {}
        policy = resolve_ticket_destroy_policy(details)
        if not policy["destroy_after_migrate"]:
            return
        cluster_ids = _collect_destroy_dts_cluster_ids(ticket)
        if not cluster_ids:
            return
        if _has_related_destroy_for_clusters(ticket, cluster_ids):
            logger.info(gettext_runtime("迁移单据 {} 已关联 DTS 集群 {} 的销毁单，跳过重复创建").format(ticket.id, cluster_ids))
            return

        recycle_hosts = policy["recycle_hosts"]
        if len(cluster_ids) == 1:
            destroy_details = {"dts_cluster_id": cluster_ids[0], "recycle_hosts": recycle_hosts}
        else:
            destroy_details = {"dts_cluster_ids": cluster_ids, "recycle_hosts": recycle_hosts}

        destroy_ticket = Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_DTS_CLUSTER_DESTROY,
            creator=ticket.creator,
            bk_biz_id=ticket.bk_biz_id,
            remark=gettext_runtime("迁移单据{}成功后自动销毁 DTS").format(ticket.id),
            details=destroy_details,
            auto_execute=True,
        )
        ticket.add_related_ticket(destroy_ticket, done=True)
    except Exception as e:
        logger.error(gettext_runtime("迁移单据 {} 串联销毁 DTS 失败: {}").format(getattr(ticket, "id", None), str(e)))


class DtsMigrateFlowParamBuilder(builders.FlowParamBuilder):
    """三种 DTS 迁移单据共用：写入 ticket_id；可选整单 migrate_type。

    migrate_plan 由 flow 内 build_migrate_plan(self.data) 构建，勿写入 ticket_data（不可 JSON 序列化）。
    """

    migrate_type = None

    def format_ticket_data(self):
        self.ticket_data["ticket_id"] = self.ticket.id
        if self.migrate_type:
            self.ticket_data["migrate_type"] = self.migrate_type
        # 行内 resource_spec 提升到顶层，供 inner flow 的 patch_resource_spec 读取
        self.ticket_data["resource_spec"] = _resolve_resource_spec(self.ticket_data)


class DtsMigrateFlowBuilder(BaseMySQLTicketFlowBuilder):
    """三种 DTS 迁移单据共用 patch_ticket_detail。"""

    @property
    def need_resource_pool(self):
        """是否需要资源申请节点。"""
        return True

    def patch_ticket_detail(self):
        _patch_migrate_task_names(self.ticket)
        _patch_migrate_deploy_cluster_names(self.ticket)
        # 预置资源申请回写的 nodes 结构到 ticket.details 顶层（与 resource_spec 的 master/worker 角色对齐）。
        # 放在 patch_ticket_detail 而非 ResourceApplyParamBuilder.format：两者都在建单事务内，
        # 但 patch_ticket_detail 更早、且不依赖资源申请是否执行/是否失败回滚，确保建单后 details 始终含 nodes 占位；
        # 资源申请成功后由 flow_manager.resource.ResourceApplyFlow.update_details(nodes=node_infos) 用真实机器覆盖。
        self.ticket.details.setdefault("nodes", {role: [] for role in _DTS_DEPLOY_ROLES})
        # 规格映射：resource_spec 里的 spec_id → Spec 详情，写入 details 顶层供详情接口返回
        self.ticket.details["specs"] = _resolve_specs_map(self.ticket.details)
        super().patch_ticket_detail()


class DtsMigrateResourceParamBuilder(builders.ResourceApplyParamBuilder):
    """三种 DTS 迁移单据共用资源申请。

    资源池模式下：deploy 本单部署 Master/Worker 主机由资源申请回填，
    调用方仅传 resource_spec；申请完成后在 post_callback 把申请到的 IP 写回
    dts_resource.deploy.master_hosts / worker_hosts（即 dtshost 参数）。
    """

    def format(self):
        # 资源申请 Flow 需要顶层 bk_cloud_id，fetch_apply_params 强制取值，必须写入（缺省 0=直连区域）
        deploys = _iter_dts_deploys(self.ticket_data)
        bk_cloud_id = 0
        for deploy in deploys:
            bk_cloud_id = int(deploy.get("bk_cloud_id") or 0)
            if bk_cloud_id:
                break
        self.ticket_data["bk_cloud_id"] = bk_cloud_id
        # 行内 resource_spec 提升到顶层，供 flow_manager.resource.fetch_apply_params 读取
        # （ticket_data 是 details 的深拷贝，不影响原始 details 结构）
        self.ticket_data["resource_spec"] = _resolve_resource_spec(self.ticket_data)
        # Flow 参数（self.ticket_data 是 details 的深拷贝）预置 nodes 占位；
        # 真实机器由 flow_manager.resource.ResourceApplyFlow 申请成功后写回 details.nodes
        self.ticket_data.setdefault("nodes", {role: [] for role in _DTS_DEPLOY_ROLES})

    @classmethod
    def _collect_hosts(cls, nodes: dict, role: str) -> list:
        """从资源申请回写的 ticket.details['nodes'][role] 提取 {ip, bk_cloud_id}。"""
        hosts = []
        for node in (nodes or {}).get(role) or []:
            ip = node.get("ip")
            if not ip:
                continue
            hosts.append({"ip": ip, "bk_cloud_id": int(node.get("bk_cloud_id") or 0)})
        return hosts

    @classmethod
    def _fill_deploy_hosts(cls, details: dict, master_hosts: list, worker_hosts: list) -> bool:
        """把申请到的 IP 回填进 details 中所有含 deploy 的 dts_resource.deploy。

        单行单 deploy 或多行 infos 每行各一个 deploy 均覆盖。返回是否发生回填。
        """
        changed = False
        infos = details.get("infos") or []
        if infos:
            for row in infos:
                deploy = (row.get("dts_resource") or {}).get("deploy")
                if deploy:
                    deploy["master_hosts"] = master_hosts
                    deploy["worker_hosts"] = worker_hosts
                    changed = True
        else:
            deploy = (details.get("dts_resource") or {}).get("deploy")
            if deploy:
                deploy["master_hosts"] = master_hosts
                deploy["worker_hosts"] = worker_hosts
                changed = True
        return changed

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        # 资源申请 Flow 把申请到的主机写回 inner flow 的 ticket_data 快照 nodes[role]
        nodes = ticket_data.get("nodes") or {}
        master_hosts = self._collect_hosts(nodes, "master")
        worker_hosts = self._collect_hosts(nodes, "worker")
        if not master_hosts or not worker_hosts:
            logger.warning(gettext_runtime("DTS 迁移资源申请回填失败: master={}, worker={}").format(master_hosts, worker_hosts))
            return
        self._fill_deploy_hosts(ticket_data, master_hosts, worker_hosts)
        # 同步回写整个 ticket.details，保证后续查询/重建 plan 一致
        self._fill_deploy_hosts(self.ticket.details, master_hosts, worker_hosts)
        next_flow.save(update_fields=["details"])
        self.ticket.save(update_fields=["details"])


class MysqlToMysqlMigrateFlowParamBuilder(DtsMigrateFlowParamBuilder):
    controller = MySQLController.mysql_to_mysql_migrate_scene
    migrate_type = "mysql_to_mysql"


@builders.BuilderFactory.register(TicketType.MYSQL_DTS_DATA_MIGRATE, iam=ActionEnum.MYSQL_DTS_DATA_MIGRATE)
class MysqlToMysqlMigrateFlowBuilder(DtsMigrateFlowBuilder):
    serializer = MysqlToMysqlMigrateDetailSerializer
    inner_flow_builder = MysqlToMysqlMigrateFlowParamBuilder
    inner_flow_name = _("MySQL 数据迁移")
    resource_apply_builder = DtsMigrateResourceParamBuilder


class MysqlHaToClusterMigrateFlowParamBuilder(DtsMigrateFlowParamBuilder):
    controller = MySQLController.mysql_ha_to_cluster_migrate_scene
    migrate_type = "ha_to_cluster"


@builders.BuilderFactory.register(TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE)
class MysqlHaToClusterMigrateFlowBuilder(DtsMigrateFlowBuilder):
    serializer = MysqlMigrateBaseDetailSerializer
    inner_flow_builder = MysqlHaToClusterMigrateFlowParamBuilder
    inner_flow_name = _("MySQL HA到Cluster数据迁移")
    resource_apply_builder = DtsMigrateResourceParamBuilder


class MysqlRenameMigrateFlowParamBuilder(DtsMigrateFlowParamBuilder):
    controller = MySQLController.mysql_rename_migrate_scene
    # 不整单写死 migrate_type：由 Serializer / Flow 按行推断


@builders.BuilderFactory.register(TicketType.MYSQL_DTS_DATA_MIGRATE_RENAME, iam=ActionEnum.MYSQL_DTS_DATA_MIGRATE)
class MysqlRenameMigrateFlowBuilder(DtsMigrateFlowBuilder):
    serializer = MysqlRenameMigrateDetailSerializer
    inner_flow_builder = MysqlRenameMigrateFlowParamBuilder
    inner_flow_name = _("MySQL 重命名迁移")
    resource_apply_builder = DtsMigrateResourceParamBuilder
