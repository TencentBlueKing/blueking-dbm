# -*- coding: utf-8 -*-
"""MongoDB DTS（MongoShake）同步单据。"""

import logging
import re

from django.utils.translation import gettext as gettext_runtime
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.components import CCApi
from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.exec_host.models import ExecHost, ExecHostStatus
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.flow.utils.mongodb.mongoshake_conf import (
    SOURCE_CONNECT_MODES,
    STOP_MODES,
    namespace_list,
    normalize_source_connect_mode,
    normalize_stop_mode,
)
from backend.flow.utils.mongodb.version_utils import compare_mongodb_versions
from backend.ticket import builders
from backend.ticket.builders.common.base import CommonValidate
from backend.ticket.builders.mongodb.base import (
    BaseMongoDBOperateDetailSerializer,
    BaseMongoDBTicketFlowBuilder,
    BaseMongoOperateFlowParamBuilder,
)
from backend.ticket.constants import TicketType
from backend.ticket.exceptions import TicketResourceApplyException

logger = logging.getLogger("root")

_DTS_CLUSTER_TYPES = (
    ClusterType.MongoReplicaSet.value,
    ClusterType.MongoShardedCluster.value,
)
_SOURCE_ROOT_ID_RE = re.compile(r"^[0-9a-f]{14}$")
_ACTIVE_EXEC_HOST = (ExecHostStatus.DEPLOYING.value, ExecHostStatus.RUNNING.value)
# 资源申请角色名。申请后 ResourceBatchApplyFlow 把主机列表写到 infos[i]["exec_host"]，post_callback 再转成单个主机。
EXEC_HOST_ROLE = "exec_host"


def exec_host_spec(row: dict) -> dict:
    return ((row or {}).get("resource_spec") or {}).get(EXEC_HOST_ROLE) or {}


class _ExecHostSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("执行机 IP"), required=False, allow_blank=True, default="")


class MongoDBDtsDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class DtsInfoSerializer(serializers.Serializer):
        source_cluster_id = serializers.IntegerField(help_text=_("源集群ID"))
        target_cluster_id = serializers.IntegerField(help_text=_("目标集群ID"))
        namespaces = serializers.ListField(
            help_text=_("同步命名空间（库或库.表，无通配）"),
            child=serializers.CharField(),
            required=False,
            default=list,
        )
        transform_namespace = serializers.CharField(
            help_text=_("命名空间映射"), required=False, allow_blank=True, default=""
        )
        source_connect_mode = serializers.ChoiceField(
            help_text=_("副本集源端连接模式；分片源固定直连各 shard backup"),
            choices=list(SOURCE_CONNECT_MODES),
            required=False,
            default="secondaryPreferred",
        )
        stop_mode = serializers.ChoiceField(
            help_text=_("auto 追平后自动停；manual 追平后人工确认再停"),
            choices=list(STOP_MODES),
            required=False,
            default="auto",
        )
        exec_host_id = serializers.IntegerField(help_text=_("复用已有执行机"), required=False, allow_null=True)
        exec_host = _ExecHostSerializer(help_text=_("新建执行机（手填业务空闲机 IP）"), required=False)
        resource_spec = serializers.JSONField(
            help_text=_("资源池申请执行机：{exec_host: {spec_id, labels, label_names}}"), required=False, default=dict
        )
        exec_host_name = serializers.CharField(help_text=_("执行机名称"), required=False, allow_blank=True, default="")
        recycle_exec_host = serializers.BooleanField(help_text=_("结束后是否回收执行机"), required=False, default=True)
        require_target_sharded = serializers.BooleanField(
            help_text=_("目标为分片时是否强制检查已 shardCollection，默认否"),
            required=False,
            default=False,
        )

        def validate(self, attrs):
            if attrs["source_cluster_id"] == attrs["target_cluster_id"]:
                raise serializers.ValidationError(_("源集群和目标集群不能相同"))
            try:
                namespace_list(attrs.get("namespaces") or [])
                normalize_source_connect_mode(attrs.get("source_connect_mode"))
                normalize_stop_mode(attrs.get("stop_mode"))
            except ValueError as err:
                raise serializers.ValidationError(str(err))
            exec_host_id = attrs.get("exec_host_id")
            exec_host = attrs.get("exec_host") or {}
            ip = (exec_host.get("ip") or "").strip()
            spec = exec_host_spec(attrs)
            if not isinstance(attrs.get("resource_spec"), dict) or set(attrs["resource_spec"]) - {EXEC_HOST_ROLE}:
                raise serializers.ValidationError(_("resource_spec 只支持 exec_host"))
            if spec and not spec.get("spec_id"):
                raise serializers.ValidationError(_("资源池申请执行机必须选择规格"))
            sources = [bool(exec_host_id), bool(ip), bool(spec)]
            if sum(sources) != 1:
                raise serializers.ValidationError(_("执行机来源只能是资源池申请、执行机 IP、执行机 ID 之一"))
            return attrs

    infos = serializers.ListSerializer(help_text=_("DTS 同步信息"), child=DtsInfoSerializer(), allow_empty=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if len(attrs["infos"]) != 1:
            raise serializers.ValidationError(_("当前仅支持单条 DTS 任务"))
        info = attrs["infos"][0]
        cluster_ids = {info["source_cluster_id"], info["target_cluster_id"]}
        clusters = {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)}
        missing = cluster_ids - set(clusters)
        if missing:
            raise serializers.ValidationError(_("集群不存在: {}").format(",".join(map(str, missing))))
        src = clusters[info["source_cluster_id"]]
        dst = clusters[info["target_cluster_id"]]
        if src.cluster_type not in _DTS_CLUSTER_TYPES or dst.cluster_type not in _DTS_CLUSTER_TYPES:
            raise serializers.ValidationError(_("仅支持副本集与分片集群: {} -> {}").format(src.cluster_type, dst.cluster_type))
        try:
            if compare_mongodb_versions(dst.major_version, src.major_version) < 0:
                raise serializers.ValidationError(_("目标版本 {} 低于源版本 {}").format(dst.major_version, src.major_version))
        except ValueError as err:
            raise serializers.ValidationError(_("major_version 无效: {}").format(err))
        if src.bk_cloud_id != dst.bk_cloud_id:
            raise serializers.ValidationError(_("源与目标云区域不一致: {} vs {}").format(src.bk_cloud_id, dst.bk_cloud_id))
        exec_host_id = info.get("exec_host_id")
        if exec_host_id:
            job = ExecHost.objects.filter(id=exec_host_id, status__in=_ACTIVE_EXEC_HOST).first()
            if not job:
                raise serializers.ValidationError(_("执行机 id={} 不存在或未处于可用状态").format(exec_host_id))
            if job.bk_cloud_id != src.bk_cloud_id:
                raise serializers.ValidationError(_("执行机云区域与源集群不一致"))
        elif not exec_host_spec(info):
            ip = info["exec_host"]["ip"].strip()
            self._validate_new_exec_host_ip(self.context["bk_biz_id"], src.bk_cloud_id, ip)
            info["exec_host"]["ip"] = ip
        return attrs

    @staticmethod
    def _validate_new_exec_host_ip(bk_biz_id: int, bk_cloud_id: int, ip: str):
        """新执行机必须是本业务空闲机池里、未被 DBM 使用的主机：流程会在上面以 root 执行，结束后回收。"""
        if Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).exists():
            raise serializers.ValidationError(_("执行机 IP {} 已被 DBM 使用，复用执行机请传执行机 ID").format(ip))
        resp = CCApi.list_biz_hosts(
            {
                "bk_biz_id": bk_biz_id,
                "fields": ["bk_host_id", "bk_host_innerip", "bk_cloud_id"],
                "page": {"start": 0, "limit": 10},
                "host_property_filter": {
                    "condition": "AND",
                    "rules": [
                        {"field": "bk_host_innerip", "operator": "equal", "value": ip},
                        {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
                    ],
                },
            },
            use_admin=True,
        )
        host_ids = [host["bk_host_id"] for host in resp.get("info") or []]
        if not host_ids:
            raise serializers.ValidationError(_("执行机 IP {} 不在业务 {} 云区域 {} 下").format(ip, bk_biz_id, bk_cloud_id))
        CommonValidate.validate_hosts_from_idle_pool(bk_biz_id, host_ids)


class MongoDBDtsFlowParamBuilder(BaseMongoOperateFlowParamBuilder):
    controller = MongoDBController.mongo_dts


class MongoDBDtsResourceParamBuilder(builders.ResourceApplyParamBuilder):
    """按行申请执行机（ResourceBatchApplyFlow），申请后把主机回填到 infos[i].exec_host。"""

    # 复用执行机或手填 IP 的行不申请
    allow_resource_empty = True

    def validate_spec(self):
        for row in self.ticket_data.get("infos") or []:
            spec = exec_host_spec(row)
            if spec and not spec.get("spec_id"):
                raise TicketResourceApplyException(gettext_runtime("申请资源的规格id不能为0或为空"))

    def format(self):
        # ResourceBatchApplyFlow 按行读取 resource_spec 和 bk_cloud_id；地域默认取源集群
        cluster_ids = [row["source_cluster_id"] for row in self.ticket_data.get("infos") or []]
        clusters = {cluster.id: cluster for cluster in Cluster.objects.filter(id__in=cluster_ids)}
        for row in self.ticket_data.get("infos") or []:
            cluster = clusters[row["source_cluster_id"]]
            row["bk_cloud_id"] = cluster.bk_cloud_id
            row["resource_spec"] = row.get("resource_spec") or {}
            spec = exec_host_spec(row)
            if not spec:
                continue
            spec["count"] = 1
            spec.setdefault("affinity", AffinityEnum.NONE.value)
            if cluster.region and cluster.region != "default":
                spec.setdefault("location_spec", {"city": cluster.region, "sub_zone_ids": []})

    @staticmethod
    def _applied_host(nodes) -> dict:
        node = (nodes or [None])[0] if isinstance(nodes, list) else nodes
        if not node or not node.get("ip"):
            return {}
        return {"ip": node["ip"], "bk_host_id": node.get("bk_host_id"), "bk_cloud_id": node.get("bk_cloud_id")}

    def post_callback(self):
        next_flow = self.ticket.next_flow()
        ticket_data = next_flow.details["ticket_data"]
        nodes = self.ticket.details.get("nodes") or {}
        for idx, row in enumerate(ticket_data.get("infos") or []):
            if not exec_host_spec(row):
                continue
            host = self._applied_host(row.get(EXEC_HOST_ROLE)) or self._applied_host(
                nodes.get(f"{idx}_{EXEC_HOST_ROLE}")
            )
            if not host:
                raise TicketResourceApplyException(gettext_runtime("资源申请未返回执行机"))
            row[EXEC_HOST_ROLE] = host
            self.ticket.details["infos"][idx][EXEC_HOST_ROLE] = host
        next_flow.save(update_fields=["details"])
        self.ticket.save(update_fields=["details", "update_at"])


@builders.BuilderFactory.register(TicketType.MONGODB_DTS, is_recycle=True)
class MongoDBDtsFlowBuilder(BaseMongoDBTicketFlowBuilder):
    """回收类单据：流程下架执行机时写入 recycle_hosts，单据成功后发起主机回收单。"""

    serializer = MongoDBDtsDetailSerializer
    inner_flow_builder = MongoDBDtsFlowParamBuilder
    inner_flow_name = _("MongoDB DTS 同步执行")
    resource_batch_apply_builder = MongoDBDtsResourceParamBuilder

    @property
    def need_resource_pool(self):
        return any(exec_host_spec(row) for row in self.ticket.details.get("infos") or [])


class MongoDBDtsCleanupDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class CleanupInfoSerializer(serializers.Serializer):
        source_root_id = serializers.CharField(help_text=_("失败的 DTS 流程 root_id"), required=False, allow_blank=True)
        source_cluster_id = serializers.IntegerField(help_text=_("源集群ID"))
        target_cluster_id = serializers.IntegerField(help_text=_("目标集群ID"))
        exec_host_id = serializers.IntegerField(help_text=_("执行机 ID"), required=False, allow_null=True)
        exec_host = _ExecHostSerializer(help_text=_("执行机 IP（无 id 时）"), required=False)
        recycle_exec_host = serializers.BooleanField(help_text=_("是否回收执行机"), required=False, default=True)

        def validate(self, attrs):
            exec_host_id = attrs.get("exec_host_id")
            ip = ((attrs.get("exec_host") or {}).get("ip") or "").strip()
            if not exec_host_id and not ip:
                raise serializers.ValidationError(_("清理必须提供执行机 ID 或执行机 IP"))
            return attrs

    source_root_id = serializers.CharField(help_text=_("失败的 DTS 流程 root_id"), required=False, allow_blank=True)
    infos = serializers.ListSerializer(help_text=_("DTS 清理信息"), child=CleanupInfoSerializer(), allow_empty=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if len(attrs["infos"]) != 1:
            raise serializers.ValidationError(_("当前仅支持单条 DTS 清理任务"))
        root_id = (attrs.get("source_root_id") or "").strip()
        if not root_id:
            root_id = (attrs["infos"][0].get("source_root_id") or "").strip()
        if not root_id:
            raise serializers.ValidationError(_("source_root_id 必填"))
        if not _SOURCE_ROOT_ID_RE.match(root_id):
            raise serializers.ValidationError(_("source_root_id 格式无效，期望 ^[0-9a-f]{14}$"))
        attrs["source_root_id"] = root_id
        attrs["infos"][0]["source_root_id"] = root_id
        cluster_ids = {attrs["infos"][0]["source_cluster_id"], attrs["infos"][0]["target_cluster_id"]}
        found = set(Cluster.objects.filter(id__in=cluster_ids).values_list("id", flat=True))
        missing = cluster_ids - found
        if missing:
            raise serializers.ValidationError(_("集群不存在: {}").format(",".join(map(str, missing))))
        return attrs


class MongoDBDtsCleanupFlowParamBuilder(BaseMongoOperateFlowParamBuilder):
    controller = MongoDBController.mongo_dts_cleanup


@builders.BuilderFactory.register(TicketType.MONGODB_DTS_CLEANUP, is_recycle=True)
class MongoDBDtsCleanupFlowBuilder(BaseMongoDBTicketFlowBuilder):
    serializer = MongoDBDtsCleanupDetailSerializer
    inner_flow_builder = MongoDBDtsCleanupFlowParamBuilder
    inner_flow_name = _("MongoDB DTS 清理执行")
