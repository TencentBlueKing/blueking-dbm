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
import os
from typing import Dict, List, Optional, Tuple

from django.db.models import Q
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstancePhase
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum, MongoDBClusterRole
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.engine.bamboo.scene.mongodb.sub_task.upgrade_version import MongoUpgradeVersionSubTask
from backend.flow.plugins.components.collections.mongodb.mongo_update_version import MongoUpdateVersionComponent
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoNode, MongoRepository, ReplicaSet
from backend.flow.utils.mongodb.mongodb_util import MongoUtil
from backend.flow.utils.mongodb.version_utils import normalize_mongodb_full_version

logger = logging.getLogger("flow")

_MONGO_CLUSTER_TYPES = (ClusterType.MongoReplicaSet.value, ClusterType.MongoShardedCluster.value)
MONGODB_MAJOR_MINOR_UPGRADE_CHAIN = (
    "3.0",
    "3.2",
    "3.4",
    "3.6",
    "4.0",
    "4.2",
    "4.4",
    "5.0",
    "6.0",
    "7.0",
)
_UPGRADE_CHAIN_INDEX = {v: i for i, v in enumerate(MONGODB_MAJOR_MINOR_UPGRADE_CHAIN)}


class MongoUpgradeVersionFlow(MongoBaseFlow):
    class Serializer(serializers.Serializer):
        class InfoRow(serializers.Serializer):
            cluster_id_list = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
            current_version = serializers.CharField()
            dest_version = serializers.CharField()
            strategy = serializers.ChoiceField(choices=["rolling", "full_stop"])
            bk_cloud_id = serializers.IntegerField()

            def validate(self, attrs):
                if attrs["current_version"] == attrs["dest_version"]:
                    raise serializers.ValidationError("dest_version can not be equal to current_version")
                return attrs

        uid = serializers.CharField()
        ticket_id = serializers.CharField()
        bk_biz_id = serializers.IntegerField()
        bk_cloud_id = serializers.IntegerField()
        ticket_type = serializers.ChoiceField(choices=["MONGODB_UPGRADE_VERSION"])
        created_by = serializers.CharField()
        infos = InfoRow(many=True, allow_empty=False)

    def __init__(self, root_id: str, data: Optional[Dict]):
        super().__init__(root_id, data)
        self.cluster_infos: List[Dict] = []
        self.global_hops: List[Tuple[str, str]] = []
        self._unique_ticket_nodes: List[MongoNode] = []
        self._validate_and_normalize()

    def _validate_and_normalize(self):
        serializer = self.Serializer(data=self.payload)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        cluster_id_list = []
        for row in payload["infos"]:
            cluster_id_list.extend(row["cluster_id_list"])
        self.check_cluster_id_list(cluster_id_list)
        clusters = MongoRepository.fetch_many_cluster_dict(id__in=cluster_id_list)

        for info in payload["infos"]:
            for cluster_id in info["cluster_id_list"]:
                cluster = clusters.get(cluster_id)
                self.check_cluster_valid(cluster, payload)
                current_version_mm = self._version_major_minor(info["current_version"])
                dest_version_mm = self._version_major_minor(info["dest_version"])
                hops = self._expand_upgrade_hops(
                    current_version_mm=current_version_mm, dest_version_mm=dest_version_mm
                )
                hop_plans = []
                for from_version_mm, to_version_mm in hops:
                    target_pkg = self._get_target_package(to_version_mm)
                    hop_plans.append(
                        {
                            "current_version": from_version_mm,
                            "dest_version": to_version_mm,
                            "display_current_version": info["current_version"],
                            "display_dest_version": info["dest_version"],
                            "target_pkg": target_pkg,
                            "pkg_version": target_pkg.version,
                            "persist_version": self._resolve_persist_version(
                                target_pkg=target_pkg, dest_version=to_version_mm
                            ),
                        }
                    )
                hop_plan_map = {(p["current_version"], p["dest_version"]): p for p in hop_plans}
                self.cluster_infos.append(
                    {
                        "cluster": cluster,
                        "info": info,
                        "exec_groups": self._build_exec_groups(cluster),
                        "hop_plans": hop_plans,
                        "hop_plan_map": hop_plan_map,
                    }
                )
        if self.cluster_infos:

            def _hop_sequence(item: Dict) -> Tuple[Tuple[str, str], ...]:
                return tuple((p["current_version"], p["dest_version"]) for p in item["hop_plans"])

            first_seq = _hop_sequence(self.cluster_infos[0])
            for item in self.cluster_infos[1:]:
                if _hop_sequence(item) != first_seq:
                    # 与 global_hops barrier、同机多实例介质替换节奏一致；路径不同会导致 hop 对齐与运维风险。
                    raise serializers.ValidationError(
                        _("同一工单内各集群的 MongoDB 主次版本升级阶梯必须一致，" "以便同机多实例在同一 hop 完成后再进入下一版本。")
                    )
            self.global_hops = list(first_seq)
            seen_nodes = set()
            self._unique_ticket_nodes = []
            for item in self.cluster_infos:
                for node in self._collect_all_nodes(item["exec_groups"]):
                    key = (node.bk_cloud_id, node.ip, node.port)
                    if key not in seen_nodes:
                        seen_nodes.add(key)
                        self._unique_ticket_nodes.append(node)
        self._validate_hosts_multi_instance_all_clusters_in_ticket(
            cluster_infos=self.cluster_infos,
            ticket_cluster_ids=set(cluster_id_list),
            bk_biz_id=payload["bk_biz_id"],
        )
        logger.info(
            "MongoUpgradeVersionFlow payload normalized, clusters=%s",
            [i["cluster"].cluster_id for i in self.cluster_infos],
        )

    @staticmethod
    def _validate_hosts_multi_instance_all_clusters_in_ticket(
        *,
        cluster_infos: List[Dict],
        ticket_cluster_ids: set,
        bk_biz_id: int,
    ) -> None:
        """
        同一主机若存在多个 MongoDB 实例（多集群混部等），共享 mongod/mongos 介质升级须同窗单覆盖该机所有相关集群。
        """
        nodes = []
        for item in cluster_infos:
            nodes.extend(MongoUpgradeVersionFlow._collect_all_nodes(item["exec_groups"]))
        hosts = {(n.bk_cloud_id, n.ip) for n in nodes}
        for bk_cloud_id, ip in sorted(hosts):
            base_q = dict(
                machine__bk_cloud_id=bk_cloud_id,
                machine__ip=ip,
                bk_biz_id=bk_biz_id,
                cluster_type__in=_MONGO_CLUSTER_TYPES,
                phase=InstancePhase.ONLINE.value,
            )
            storages = StorageInstance.objects.filter(**base_q).prefetch_related("cluster")
            proxies = ProxyInstance.objects.filter(**base_q).prefetch_related("cluster")
            inst_count = storages.count() + proxies.count()
            if inst_count <= 1:
                continue
            cluster_ids_on_host = set()
            for s in storages:
                cluster_ids_on_host.update(c.id for c in s.cluster.all())
            for p in proxies:
                cluster_ids_on_host.update(c.id for c in p.cluster.all())
            missing = cluster_ids_on_host - ticket_cluster_ids
            if missing:
                raise serializers.ValidationError(
                    _(
                        "主机 {ip}（云区域 {bk_cloud_id}）上存在 {n} 个 MongoDB 实例，涉及多个集群；"
                        "升级须在同一工单中一并选择相关集群。当前未包含的集群 id：{missing}；"
                        "本工单已选集群 id：{selected}。"
                    ).format(
                        ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        n=inst_count,
                        missing=sorted(missing),
                        selected=sorted(ticket_cluster_ids),
                    )
                )

    @staticmethod
    def _version_major_minor(version: str) -> str:
        v = version.removeprefix("mongodb-")
        parts = v.split(".", 2)
        return ".".join(parts[:2]) if len(parts) >= 2 else v

    @staticmethod
    def _expand_upgrade_hops(current_version_mm: str, dest_version_mm: str) -> List[Tuple[str, str]]:
        if current_version_mm not in _UPGRADE_CHAIN_INDEX:
            raise serializers.ValidationError(_("不支持的当前版本：{}").format(current_version_mm))
        if dest_version_mm not in _UPGRADE_CHAIN_INDEX:
            raise serializers.ValidationError(_("不支持的目标版本：{}").format(dest_version_mm))
        current_idx = _UPGRADE_CHAIN_INDEX[current_version_mm]
        dest_idx = _UPGRADE_CHAIN_INDEX[dest_version_mm]
        if dest_idx <= current_idx:
            raise serializers.ValidationError(_("目标版本必须高于当前版本：{} -> {}").format(current_version_mm, dest_version_mm))
        chain = MONGODB_MAJOR_MINOR_UPGRADE_CHAIN[current_idx : dest_idx + 1]
        return [(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]

    @classmethod
    def _get_target_package(cls, dest_version_mm: str) -> Package:
        candidate_versions = [
            dest_version_mm,
            f"{dest_version_mm}.0",
            f"mongodb-{dest_version_mm}",
            f"mongodb-{dest_version_mm}.0",
        ]
        for version in candidate_versions:
            try:
                return Package.get_latest_package(version=version, pkg_type=MediumEnum.MongoDB, db_type=DBType.MongoDB)
            except Exception:
                continue
        # Fallback: pick latest package whose version starts with major.minor (e.g. 3.6 -> 3.6.0/3.6.18)
        package = (
            Package.objects.filter(
                Q(version__startswith=f"{dest_version_mm}.")
                | Q(version__iexact=dest_version_mm)
                | Q(version__istartswith=f"mongodb-{dest_version_mm}")
                | Q(name__icontains=f"mongodb-{dest_version_mm}")
                | Q(name__icontains=f"mongo-{dest_version_mm}"),
                pkg_type=MediumEnum.MongoDB,
                db_type=DBType.MongoDB,
                enable=True,
            )
            .order_by("-update_at")
            .first()
        )
        if package:
            return package
        raise serializers.ValidationError(_("未找到目标版本 {} 的可用介质包").format(dest_version_mm))

    def _build_exec_groups(self, cluster: MongoDBCluster) -> Dict:
        # backup member must be the first one, then numbered members.
        def rs_members(rs: ReplicaSet) -> List[MongoNode]:
            return [n for n in [rs.get_backup_node(), *rs.get_not_backup_nodes()] if n]

        groups = {"replicasets": [], "mongos": []}
        if cluster.cluster_type == ClusterType.MongoReplicaSet:
            groups["replicasets"].append({"name": cluster.name, "members": rs_members(cluster.get_shards()[0])})
        elif cluster.cluster_type == ClusterType.MongoShardedCluster:
            for shard in cluster.get_shards(with_config=True, sort_by_set_name=True):
                groups["replicasets"].append({"name": shard.set_name, "members": rs_members(shard)})
            groups["mongos"] = sorted(cluster.get_mongos(), key=lambda n: (n.ip, n.port))
        else:
            raise Exception(_("unsupported cluster type {}".format(cluster.cluster_type)))
        return groups

    def start(self):
        pipeline = Builder(root_id=self.root_id, data=self.payload)
        actuator_workdir = MongoUtil().get_mongodb_os_conf()["file_path"]
        file_set = set()
        host_set = set()
        get_file_list = GetFileList(db_type=DBType.MongoDB)
        for item in self.cluster_infos:
            cluster = item["cluster"]
            for hop_plan in item["hop_plans"]:
                for pkg in get_file_list.mongodb_pkg(db_version=hop_plan["pkg_version"]):
                    for ip in cluster.get_iplist():
                        file_set.add(pkg)
                        host_set.add((cluster.get_bk_cloud_id(), ip))

        if file_set and host_set:
            send_media_act = SendMedia.act(
                act_name=_("MongoDB-升级介质下发"),
                file_list=list(file_set),
                bk_host_list=[{"ip": ip, "bk_cloud_id": bk_cloud_id} for bk_cloud_id, ip in sorted(host_set)],
                file_target_path=actuator_workdir,
            )
            pipeline.add_parallel_acts([send_media_act])
        if self._unique_ticket_nodes:
            pre_upgrade_check_sf = self._build_pre_upgrade_check_sub_flow(file_path=actuator_workdir)
            if pre_upgrade_check_sf:
                pipeline.add_sub_pipeline(pre_upgrade_check_sf)
        for hop in self.global_hops:
            pipeline.add_sub_pipeline(self._build_hop_stage_sub_flow(hop=hop, file_path=actuator_workdir))
        pipeline.run_pipeline()

    @staticmethod
    def _collect_all_nodes(exec_groups: Dict) -> List[MongoNode]:
        nodes = []
        for rs_group in exec_groups["replicasets"]:
            nodes.extend(rs_group["members"])
        nodes.extend(exec_groups.get("mongos", []))
        return nodes

    @staticmethod
    def _one_representative_node_per_host(nodes: List[MongoNode]) -> List[MongoNode]:
        """Each (bk_cloud_id, ip) keeps the instance with the smallest port (stable representative for disk precheck)."""
        groups: Dict[Tuple[int, str], List[MongoNode]] = {}
        for n in nodes:
            key = (n.bk_cloud_id, n.ip)
            groups.setdefault(key, []).append(n)
        reps = [min(members, key=lambda x: x.port) for members in groups.values()]
        return sorted(reps, key=lambda n: (n.bk_cloud_id, n.ip))

    def _build_pre_upgrade_check_sub_flow(self, file_path: str):
        # mongos 不做升级前磁盘检查（无与 mongod 同级的数据目录备份诉求）
        nodes_for_disk = [n for n in self._unique_ticket_nodes if n.role != MongoDBClusterRole.Mongos.value]
        reps = self._one_representative_node_per_host(nodes_for_disk)
        if not reps:
            return None
        sb = SubBuilder(root_id=self.root_id, data=self.payload)
        sb.add_parallel_acts(
            acts_list=[
                MongoUpgradeVersionSubTask.precheck_disk_upgrade_act(
                    file_path=file_path, exec_node=node, act_label=node.ip
                )
                for node in reps
            ]
        )
        return sb.build_sub_process(_("升级前检查"))

    def _build_hop_barrier_stage_sub_flow(self, hop: Tuple[str, str], file_path: str):
        """
        Barrier：各集群先各自 SubBuilder（内并行实例级 precheck），再外层 SubBuilder 并行挂接，
        与原先「全工单节点一层并行」执行语义等价，便于流水线按集群展示阶段检查。
        """
        from_mm, to_mm = hop
        is_last_hop = bool(self.global_hops) and hop == self.global_hops[-1]
        barrier_act_prefix = _("最终检查") if is_last_hop else _("阶段检查")

        cluster_barrier_pipes = []
        for item in self.cluster_infos:
            nodes = self._collect_all_nodes(item["exec_groups"])
            if not nodes:
                continue
            cb_sb = SubBuilder(root_id=self.root_id, data=self.payload)
            barrier_acts = [
                MongoUpgradeVersionSubTask.precheck_upgrade_act(
                    file_path=file_path,
                    exec_node=node,
                    current_version=to_mm,
                    act_prefix=barrier_act_prefix,
                )
                for node in nodes
            ]
            cb_sb.add_parallel_acts(acts_list=barrier_acts)
            cluster_barrier_pipes.append(
                cb_sb.build_sub_process(_("{}-{}").format(barrier_act_prefix, item["cluster"].name))
            )

        if not cluster_barrier_pipes:
            return None

        barrier_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        barrier_sb.add_parallel_sub_pipeline(cluster_barrier_pipes)
        return barrier_sb.build_sub_process(barrier_act_prefix)

    def _build_cluster_sub_flow(
        self,
        cluster: MongoDBCluster,
        exec_groups: Dict,
        file_path: str,
        current_version: str,
        dest_version: str,
        target_pkg: Package,
        sub_process_name: Optional[str] = None,
        *,
        include_backup: bool = True,
    ):
        cluster_sb = SubBuilder(root_id=self.root_id, data=self.payload)

        # --- precheck_upgrade_cluster: parallel check all nodes ---
        all_nodes = self._collect_all_nodes(exec_groups)
        if all_nodes:
            precheck_acts = [
                MongoUpgradeVersionSubTask.precheck_upgrade_act(
                    file_path=file_path, exec_node=node, current_version=current_version
                )
                for node in all_nodes
            ]
            cluster_sb.add_parallel_acts(acts_list=precheck_acts)

        # --- upgrade_cluster: parallel replicaset upgrades ---
        rs_parallel_pipes = []
        for rs_group in exec_groups["replicasets"]:
            rs_sb = SubBuilder(root_id=self.root_id, data=self.payload)
            for node in rs_group["members"]:
                rs_sb.add_sub_pipeline(
                    sub_flow=self._build_member_sub_flow(
                        node=node,
                        file_path=file_path,
                        instance_type="mongod",
                        current_version=current_version,
                        dest_version=dest_version,
                        target_pkg=target_pkg,
                        include_backup=include_backup,
                    )
                )
            rs_parallel_pipes.append(rs_sb.build_sub_process(_("replicaset-{}".format(rs_group["name"]))))
        if rs_parallel_pipes:
            cluster_sb.add_parallel_sub_pipeline(rs_parallel_pipes)

        # upgrade mongos after config/shard groups in one enclosed stage.
        mongos_stage = self._build_mongos_stage_sub_flow(
            exec_groups=exec_groups,
            file_path=file_path,
            current_version=current_version,
            dest_version=dest_version,
            target_pkg=target_pkg,
            include_backup=include_backup,
        )
        if mongos_stage:
            cluster_sb.add_sub_pipeline(sub_flow=mongos_stage)

        # --- postcheck_upgrade_cluster: set FCV to dest version ---
        postcheck_act = self._build_postcheck_set_fcv_act(
            exec_groups=exec_groups,
            file_path=file_path,
            current_version=current_version,
            dest_version=dest_version,
        )
        if postcheck_act:
            cluster_sb.add_act(**postcheck_act)
        persist_version_act = self._build_persist_meta_version_act(
            cluster=cluster,
            target_version=self._resolve_persist_version(target_pkg=target_pkg, dest_version=dest_version),
        )
        cluster_sb.add_act(**persist_version_act)

        process_name = sub_process_name if sub_process_name else _("mongo_upgrade_cluster_{}".format(cluster.name))
        return cluster_sb.build_sub_process(process_name)

    def _build_hop_stage_sub_flow(self, hop: Tuple[str, str], file_path: str):
        """
        单 hop：并行升级本工单内各集群，再执行 barrier 子流程（外层「阶段检查/最终检查」，
        内层按集群 SubBuilder 并行实例级 precheck），确保同机多实例均完成当前 hop 后再进入下一 hop。
        """
        from_mm, to_mm = hop
        hop_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        is_first_hop = bool(self.global_hops) and hop == self.global_hops[0]
        cluster_pipes = []
        for item in self.cluster_infos:
            plan = item["hop_plan_map"][hop]
            cluster_pipes.append(
                self._build_cluster_sub_flow(
                    cluster=item["cluster"],
                    exec_groups=item["exec_groups"],
                    file_path=file_path,
                    current_version=plan["current_version"],
                    dest_version=plan["dest_version"],
                    target_pkg=plan["target_pkg"],
                    sub_process_name=_(
                        "mongo_upgrade_cluster_{}_{}->{}".format(
                            item["cluster"].name, plan["current_version"], plan["dest_version"]
                        )
                    ),
                    include_backup=is_first_hop,
                )
            )
        if cluster_pipes:
            hop_sb.add_parallel_sub_pipeline(cluster_pipes)
        barrier_sf = self._build_hop_barrier_stage_sub_flow(hop=hop, file_path=file_path)
        if barrier_sf:
            hop_sb.add_sub_pipeline(sub_flow=barrier_sf)
        return hop_sb.build_sub_process(_("mongo_upgrade_hop_{}->{}".format(from_mm, to_mm)))

    def _build_member_sub_flow(
        self,
        node: MongoNode,
        file_path: str,
        instance_type: str,
        current_version: str,
        dest_version: str,
        target_pkg: Package,
        *,
        include_backup: bool = True,
    ):
        member_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        self._append_node_upgrade_acts(
            sb=member_sb,
            node=node,
            file_path=file_path,
            instance_type=instance_type,
            current_version=current_version,
            dest_version=dest_version,
            target_pkg=target_pkg,
            include_backup=include_backup,
        )
        return member_sb.build_sub_process(_("member-{}:{}".format(node.ip, node.port)))

    def _build_mongos_stage_sub_flow(
        self,
        exec_groups: Dict,
        file_path: str,
        current_version: str,
        dest_version: str,
        target_pkg: Package,
        *,
        include_backup: bool = True,
    ):
        mongos = exec_groups.get("mongos", [])
        if not mongos:
            return None

        mongos_sb = SubBuilder(root_id=self.root_id, data=self.payload)
        for node in mongos:
            mongos_sb.add_sub_pipeline(
                sub_flow=self._build_member_sub_flow(
                    node=node,
                    file_path=file_path,
                    instance_type="mongos",
                    current_version=current_version,
                    dest_version=dest_version,
                    target_pkg=target_pkg,
                    include_backup=include_backup,
                )
            )
        return mongos_sb.build_sub_process(_("mongos-stage"))

    @staticmethod
    def _build_postcheck_set_fcv_act(exec_groups: Dict, file_path: str, current_version: str, dest_version: str):
        mongos = exec_groups.get("mongos", [])
        if mongos:
            target_node = mongos[0]
            instance_type = "mongos"
        else:
            rs_groups = exec_groups.get("replicasets", [])
            if not rs_groups or not rs_groups[0]["members"]:
                return None
            members = rs_groups[0]["members"]
            # Any replica-set member is fine: dbactuator mongo_set_fcv resolves primary via AuthGetPrimaryInfo for mongod.
            target_node = members[0]
            instance_type = "mongod"
        return MongoUpgradeVersionSubTask.postcheck_set_fcv_act(
            file_path=file_path,
            exec_node=target_node,
            instance_type=instance_type,
            current_version=current_version,
            dest_version=dest_version,
        )

    @staticmethod
    def _resolve_persist_version(target_pkg: Optional[Package], dest_version: str) -> str:
        if target_pkg and getattr(target_pkg, "version", None):
            try:
                return normalize_mongodb_full_version(target_pkg.version)
            except ValueError:
                logger.warning(
                    "failed to normalize package version [%s], fallback to dest_version [%s]",
                    target_pkg.version,
                    dest_version,
                )
        return normalize_mongodb_full_version(dest_version)

    @staticmethod
    def _build_persist_meta_version_act(cluster: MongoDBCluster, target_version: str) -> Dict:
        return {
            "act_name": _("MongoDB-回写版本元数据-{}".format(cluster.name)),
            "act_component_code": MongoUpdateVersionComponent.code,
            "kwargs": {
                "cluster": {
                    "cluster_id_list": [cluster.cluster_id],
                    "bk_biz_id": cluster.bk_biz_id,
                    "target_version": target_version,
                }
            },
        }

    @staticmethod
    def _append_node_upgrade_acts(
        sb: SubBuilder,
        node: MongoNode,
        file_path: str,
        instance_type: str,
        current_version: str,
        dest_version: str,
        target_pkg: Package,
        *,
        include_backup: bool = True,
    ):
        sb.add_act(**MongoUpgradeVersionSubTask.shield_dbmon_act(file_path=file_path, exec_node=node))
        sb.add_act(**MongoUpgradeVersionSubTask.stop_act(file_path=file_path, exec_node=node))
        if include_backup:
            sb.add_act(
                **MongoUpgradeVersionSubTask.backup_data_act(
                    file_path=file_path,
                    exec_node=node,
                    old_full_version=normalize_mongodb_full_version(current_version),
                )
            )
        sb.add_act(
            **MongoUpgradeVersionSubTask.upgrade_binary_act(
                file_path=file_path,
                exec_node=node,
                current_version=current_version,
                dest_version=dest_version,
                instance_type=instance_type,
                pkg=os.path.basename(target_pkg.path),
                pkg_md5=target_pkg.md5,
            )
        )
        sb.add_act(**MongoUpgradeVersionSubTask.start_act(file_path=file_path, exec_node=node))
        sb.add_act(**MongoUpgradeVersionSubTask.unblock_dbmon_act(file_path=file_path, exec_node=node))
        sb.add_act(**MongoUpgradeVersionSubTask.service_check_act(file_path=file_path, exec_node=node))
