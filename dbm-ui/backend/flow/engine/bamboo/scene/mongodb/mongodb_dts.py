# -*- coding: utf-8 -*-
"""
MongoDB DTS。MongoShake collector 跑在临时 JobHost 上，追平后停掉并回收。

JobHost：单据资源池申请后的主机（infos[].job_host）或复用 infos[].job_host_id。
介质 pkg_type=mongo-dts（mongo-dts.tar.gz，包内 collector.linux），下发到 /data/mongo-dts/install/。
"""

import logging
import re
import secrets
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.models.job_host import JobHost
from backend.flow.consts import FAILED_STATES, LONG_JOB_TIMEOUT, MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.exec_shell_script import ExecShellScript
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mongodb.mongo_dts_marker import (
    MONGO_DTS_COMPONENT_CODE,
    MongoDtsMarkerComponent,
)
from backend.flow.utils.job_host import (
    JobHostDestroyInput,
    JobHostEnsureInput,
    JobHostTransData,
    add_job_host_destroy_acts,
    add_job_host_ensure_acts,
    resolve_job_host_from_row,
)
from backend.flow.utils.job_host.ensure import JOB_HOST_REGISTER_META, JOB_HOST_RESOLVE_META
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository
from backend.flow.utils.mongodb.mongodb_util import MongoUtil
from backend.flow.utils.mongodb.mongoshake_conf import (
    STOP_MODE_MANUAL,
    assert_mongoshake_supported_version,
    assert_target_user_collections_sharded_script,
    build_collector_conf,
    check_empty_target_script,
    cleanup_dts_work_script,
    collector_http_ports,
    create_user_script,
    drop_mongoshake_ckpt_script,
    drop_user_script,
    mongo_uri,
    namespace_list,
    normalize_source_connect_mode,
    normalize_stop_mode,
    replica_set_connect_uri,
    resolve_source_connect,
    start_collector_script,
    stop_collector_script,
    wait_and_stop_script,
)
from backend.flow.utils.mongodb.version_utils import compare_mongodb_versions, get_mongodb_package_v2_release

logger = logging.getLogger("flow")

# readAnyDatabase 不含 local/config；MongoShake 取位点会读 local，列举集合会碰 config。
SOURCE_ROLES = (
    '[{role:"readAnyDatabase",db:"admin"},'
    '{role:"read",db:"local"},{role:"read",db:"config"},{role:"read",db:"admin"}]'
)
TARGET_ROLES = '[{role:"readWriteAnyDatabase",db:"admin"},{role:"clusterManager",db:"admin"}]'
JOB_HOST_PURPOSE = "mongoshake_dts"
JOB_HOST_DEPLOY_PATH = "/data/mongo-dts"
DTS_ROOT_ID_TAG = "dts_root_id"
_WORK_DIR_RE = re.compile(r"^/data/mongo-dts/mongodts[A-Za-z0-9]{1,12}$")
_TEMP_USER_RE = re.compile(r"^mongodts_(src|dst)_[A-Za-z0-9]{1,12}$")
_SOURCE_ROOT_ID_RE = re.compile(r"^[0-9a-f]{14}$")
# Legacy trees (before mongo_dts marker): JobHost ensure codes used only by DTS today.
_LEGACY_DTS_COMPONENT_CODES = (JOB_HOST_REGISTER_META, JOB_HOST_RESOLVE_META)


class MongoDBDtsFlow(object):
    """在 JobHost 上跑 MongoShake，追平后停掉 collector、删临时账号并按需销毁 JobHost。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    @staticmethod
    def dts_token(root_id: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", root_id or "")[:12] or "dts"

    @classmethod
    def dts_task_identity(cls, root_id: str) -> Dict[str, str]:
        """Derive work_dir / temp users from root_id only (never trust ticket free-form paths)."""
        token = cls.dts_token(root_id)
        collector_id = "mongodts{}".format(token)
        work_dir = "{}/{}".format(JOB_HOST_DEPLOY_PATH, collector_id)
        src_user = "mongodts_src_{}".format(token)
        dst_user = "mongodts_dst_{}".format(token)
        if not _WORK_DIR_RE.match(work_dir):
            raise Exception("invalid derived work_dir: {}".format(work_dir))
        if not _TEMP_USER_RE.match(src_user) or not _TEMP_USER_RE.match(dst_user):
            raise Exception("invalid derived temp user")
        return {
            "token": token,
            "collector_id": collector_id,
            "work_dir": work_dir,
            "src_user": src_user,
            "dst_user": dst_user,
        }

    def start(self):
        row = (self.data.get("infos") or [None])[0]
        if not row:
            raise Exception("infos is empty")
        src = MongoRepository.fetch_one_cluster(id=row["source_cluster_id"])
        dst = MongoRepository.fetch_one_cluster(id=row["target_cluster_id"])
        if not src or not dst:
            raise Exception("source or target cluster not found")
        MongoBaseFlow.check_cluster_valid(src, self.data)
        MongoBaseFlow.check_cluster_valid(dst, self.data)
        if src.cluster_id == dst.cluster_id:
            raise Exception("source and target cluster are the same")
        if src.bk_cloud_id != dst.bk_cloud_id:
            raise Exception("bk_cloud_id differs: {} vs {}".format(src.bk_cloud_id, dst.bk_cloud_id))
        if compare_mongodb_versions(dst.major_version, src.major_version) < 0:
            raise Exception(
                "target major_version {} is lower than source {}".format(dst.major_version, src.major_version)
            )
        assert_mongoshake_supported_version(src.major_version)
        assert_mongoshake_supported_version(dst.major_version)
        # Sharded target is allowed when the user has already shardCollection'd on mongos.
        # MongoShake does not create shard keys; unsharded collections would land on the primary shard.

        job_host_id, job_host_ip = resolve_job_host_from_row(row, src.bk_cloud_id)
        ident = self.dts_task_identity(self.root_id)
        token = ident["token"]
        collector_id = ident["collector_id"]
        work_dir = ident["work_dir"]
        job_host_name = row.get("job_host_name") or "mongodts-{}".format(token)
        src_user, src_pwd = ident["src_user"], secrets.token_hex(16)
        dst_user, dst_pwd = ident["dst_user"], secrets.token_hex(16)
        source_connect_mode = normalize_source_connect_mode(row.get("source_connect_mode"))
        stop_mode = normalize_stop_mode(row.get("stop_mode"))
        source_urls, source_mongos, mongo_connect_mode = self._source_addrs(
            src, src_user, src_pwd, source_connect_mode
        )
        target_url = self._target_url(dst, dst_user, dst_pwd)
        full_port, incr_port = collector_http_ports(collector_id)
        conf = build_collector_conf(
            collector_id=collector_id,
            log_dir="{}/logs".format(work_dir),
            source_urls=source_urls,
            source_mongos_url=source_mongos,
            target_url=target_url,
            namespace_white=namespace_list(row.get("namespaces") or []),
            transform_namespace=row.get("transform_namespace") or "",
            full_http_port=full_port,
            incr_http_port=incr_port,
            mongo_connect_mode=mongo_connect_mode,
        )
        dts_pkg = get_mongodb_package_v2_release(MediumEnum.MongoDts.value)
        dts_file = "{}/{}/{}".format(env.BKREPO_PROJECT, env.BKREPO_BUCKET, dts_pkg.path)
        recycle = row.get("recycle_job_host", True)
        logger.info(
            "MongoDBDtsFlow collector=%s job_host=%s pkg=%s recycle=%s",
            collector_id,
            job_host_ip or "id:{}".format(job_host_id),
            dts_pkg.name,
            recycle,
        )

        pipeline = Builder(root_id=self.root_id, data=self.data)
        # Marker first: cleanup identifies DTS trees by this component code (not act-name substrings).
        pipeline.add_act(
            act_name=_("MG-DtsMarker"),
            act_component_code=MongoDtsMarkerComponent.code,
            kwargs={},
        )
        send_media_act = None
        if not job_host_id:
            send_media_act = SendMedia.act(
                act_name=_("MG-DtsSendMongoDts"),
                file_list=[dts_file],
                bk_host_list=[{"ip": job_host_ip, "bk_cloud_id": src.bk_cloud_id}],
                file_target_path=JOB_HOST_DEPLOY_PATH,
            )
        else:
            # Bind reused JobHost to this DTS root_id before pipeline runs (for cleanup校验).
            self._bind_job_host_to_dts(int(job_host_id), self.root_id)
        add_job_host_ensure_acts(
            pipeline,
            JobHostEnsureInput(
                root_id=self.root_id,
                bk_biz_id=int(self.data.get("bk_biz_id") or src.bk_biz_id),
                bk_cloud_id=src.bk_cloud_id,
                name=job_host_name,
                ip=job_host_ip,
                job_host_id=job_host_id,
                deploy_path=JOB_HOST_DEPLOY_PATH,
                version=dts_pkg.name,
                db_type=DBType.MongoDB.value,
                purpose=JOB_HOST_PURPOSE,
                tags={DTS_ROOT_ID_TAG: self.root_id},
                creator=self.data.get("created_by") or "",
                send_media_act=send_media_act,
            ),
        )
        # 脚本执行机：新建用 ticket IP；复用时 ensure 已校验，仍用库中 IP
        exec_ip = job_host_ip
        if job_host_id and not exec_ip:
            exec_ip = JobHost.objects.get(id=job_host_id).ip
        host_list = [{"ip": exec_ip, "bk_cloud_id": src.bk_cloud_id}]

        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsCheckEmptyTarget"),
                file_list=[],
                bk_host_list=[{"ip": dst.get_connect_node().ip, "bk_cloud_id": dst.bk_cloud_id}],
                exec_account="root",
                script_content=self._check_empty_script(dst),
            )
        )
        if dst.is_sharded_cluster():
            pipeline.add_act(
                **ExecShellScript.act(
                    act_name=_("MG-DtsCheckTargetSharded"),
                    file_list=[],
                    bk_host_list=[{"ip": dst.get_connect_node().ip, "bk_cloud_id": dst.bk_cloud_id}],
                    exec_account="root",
                    script_content=self._assert_sharded_script(dst),
                )
            )
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsCreateSourceUser"),
                file_list=[],
                bk_host_list=[{"ip": src.get_connect_node().ip, "bk_cloud_id": src.bk_cloud_id}],
                exec_account="root",
                script_content=self._user_script(src, src_user, src_pwd, SOURCE_ROLES),
            )
        )
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsCreateTargetUser"),
                file_list=[],
                bk_host_list=[{"ip": dst.get_connect_node().ip, "bk_cloud_id": dst.bk_cloud_id}],
                exec_account="root",
                script_content=self._user_script(dst, dst_user, dst_pwd, TARGET_ROLES),
            )
        )
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsStartMongoShake"),
                file_list=[],
                bk_host_list=host_list,
                exec_account="root",
                script_content=start_collector_script(work_dir, conf),
            )
        )
        if stop_mode == STOP_MODE_MANUAL:
            pipeline.add_act(
                act_name=_("MG-DtsManualStopConfirm"),
                act_component_code=PauseComponent.code,
                kwargs={
                    "description": _("MongoShake 持续同步中（全量端口 {} / 增量端口 {}）。确认后停止同步。").format(full_port, incr_port),
                },
            )
            pipeline.add_act(
                **ExecShellScript.act(
                    act_name=_("MG-DtsStopMongoShake"),
                    file_list=[],
                    bk_host_list=host_list,
                    exec_account="root",
                    script_content=stop_collector_script(work_dir, remove_conf=True),
                )
            )
        else:
            # 默认 auto：追平后自动停止
            pipeline.add_act(
                **ExecShellScript.act(
                    act_name=_("MG-DtsWaitCatchupAndStop"),
                    file_list=[],
                    bk_host_list=host_list,
                    exec_account="root",
                    script_content=wait_and_stop_script(work_dir, full_port, incr_port),
                    job_timeout=LONG_JOB_TIMEOUT,
                )
            )
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsDropSourceUser"),
                file_list=[],
                bk_host_list=[{"ip": src.get_connect_node().ip, "bk_cloud_id": src.bk_cloud_id}],
                exec_account="root",
                script_content=self._drop_user_script(src, src_user),
            )
        )
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsDropTargetUser"),
                file_list=[],
                bk_host_list=[{"ip": dst.get_connect_node().ip, "bk_cloud_id": dst.bk_cloud_id}],
                exec_account="root",
                script_content=self._drop_user_script(dst, dst_user),
            )
        )
        if recycle:
            add_job_host_destroy_acts(
                pipeline,
                JobHostDestroyInput(
                    root_id=self.root_id,
                    creator=self.data.get("created_by") or "",
                    job_host_id=job_host_id,
                    recycle_hosts=True,
                    # 仅销毁本流程新建的 JobHost；复用已有机时跳过
                    only_if_created=True,
                    bk_biz_id=int(self.data.get("bk_biz_id") or src.bk_biz_id),
                ),
            )
        pipeline.run_pipeline(init_trans_data_class=JobHostTransData())

    @staticmethod
    def tree_has_component(tree_data, component_code: str) -> bool:
        """Exact-match activity.component.code while walking nested sub-pipelines."""
        if not isinstance(tree_data, dict):
            return False
        activities = tree_data.get("activities") or {}
        for activity in activities.values():
            if not isinstance(activity, dict):
                continue
            component = activity.get("component") or {}
            if component.get("code") == component_code:
                return True
            nested = activity.get("pipeline")
            if nested and MongoDBDtsFlow.tree_has_component(nested, component_code):
                return True
        return False

    @classmethod
    def is_mongo_dts_flow_tree(cls, tree_data) -> bool:
        """Identify DTS by marker component code; fall back to JobHost ensure codes for legacy trees."""
        if cls.tree_has_component(tree_data, MONGO_DTS_COMPONENT_CODE):
            return True
        return any(cls.tree_has_component(tree_data, code) for code in _LEGACY_DTS_COMPONENT_CODES)

    @staticmethod
    def _bind_job_host_to_dts(job_host_id: int, dts_root_id: str) -> None:
        job = JobHost.objects.filter(id=job_host_id).first()
        if not job:
            raise Exception("JobHost id={} not found".format(job_host_id))
        tags = dict(job.tags or {})
        tags[DTS_ROOT_ID_TAG] = dts_root_id
        job.tags = tags
        job.save(update_fields=["tags"])

    @classmethod
    def assert_job_host_bound_to_dts(cls, job_host_id: int, source_root_id: str) -> None:
        """Cleanup job_host_id must belong to the failed DTS flow (tag or runtime hosts)."""
        job = JobHost.objects.filter(id=job_host_id).first()
        if not job:
            raise Exception("JobHost id={} not found".format(job_host_id))
        tags = job.tags or {}
        if str(tags.get(DTS_ROOT_ID_TAG) or "") == source_root_id:
            return
        for node in FlowNode.objects.filter(root_id=source_root_id).only("hosts"):
            for host in node.hosts or []:
                ip = host if isinstance(host, str) else (host or {}).get("ip")
                if ip and ip == job.ip:
                    return
        raise Exception("job_host_id={} is not bound to DTS source_root_id={}".format(job_host_id, source_root_id))

    @classmethod
    def resolve_failed_dts_root_id(cls, data: Optional[Dict]) -> str:
        """
        Cleanup must use the failed DTS flow's root_id (not this cleanup flow's root_id).
        Accept ticket_data.source_root_id or infos[0].source_root_id.
        Only FAILED/REVOKED trees in the same bk_biz_id may be cleaned up.
        """
        row = (data or {}).get("infos") or [None]
        row0 = row[0] if row else None
        source_root_id = str(
            (data or {}).get("source_root_id") or ((row0 or {}).get("source_root_id") if row0 else "") or ""
        ).strip()
        if not source_root_id:
            raise Exception("source_root_id of the failed DTS flow is required for cleanup")
        if not _SOURCE_ROOT_ID_RE.match(source_root_id):
            raise Exception("invalid source_root_id {!r}, expect ^[0-9a-f]{{14}}$".format(source_root_id))
        tree = FlowTree.objects.filter(root_id=source_root_id).first()
        if not tree:
            raise Exception("FlowTree not found for source_root_id={}".format(source_root_id))
        expect_biz = int((data or {}).get("bk_biz_id") or 0)
        if expect_biz and int(tree.bk_biz_id or 0) != expect_biz:
            raise Exception(
                "source_root_id {} bk_biz_id={} mismatches cleanup bk_biz_id={}".format(
                    source_root_id, tree.bk_biz_id, expect_biz
                )
            )
        if tree.status not in FAILED_STATES:
            raise Exception(
                "source_root_id {} status={} is not failed/revoked; refuse to cleanup a live DTS".format(
                    source_root_id, tree.status
                )
            )
        if not cls.is_mongo_dts_flow_tree(tree.tree):
            raise Exception("source_root_id {} is not a mongo_dts flow".format(source_root_id))
        return source_root_id

    def cleanup(self):
        """
        Manual cleanup after a failed DTS run: stop collector, drop temp users / ckpt, optionally recycle JobHost.

        work_dir / temp users are derived from the *failed* DTS root_id (source_root_id), never from
        this cleanup flow's own root_id.
        Expected ticket_data:
          source_root_id (or infos[0].source_root_id),
          infos[0].source_cluster_id, target_cluster_id,
          job_host_id (optional), recycle_job_host (default True),
          job_host_ip (required when job_host_id empty)
        """
        row = (self.data.get("infos") or [None])[0]
        if not row:
            raise Exception("infos is empty")
        src = MongoRepository.fetch_one_cluster(id=row["source_cluster_id"])
        dst = MongoRepository.fetch_one_cluster(id=row["target_cluster_id"])
        if not src or not dst:
            raise Exception("source or target cluster not found")
        failed_root_id = self.resolve_failed_dts_root_id(self.data)
        ident = self.dts_task_identity(failed_root_id)
        work_dir = ident["work_dir"]
        src_user = ident["src_user"]
        dst_user = ident["dst_user"]
        collector_id = ident["collector_id"]
        job_host_id, job_host_ip = resolve_job_host_from_row(row, src.bk_cloud_id)
        if job_host_id:
            self.assert_job_host_bound_to_dts(int(job_host_id), failed_root_id)
        exec_ip = job_host_ip
        if job_host_id and not exec_ip:
            exec_ip = JobHost.objects.get(id=job_host_id).ip
        if not exec_ip:
            raise Exception("job_host ip is required for cleanup")
        host_list = [{"ip": exec_ip, "bk_cloud_id": src.bk_cloud_id}]
        recycle = row.get("recycle_job_host", True)

        pipeline = Builder(root_id=self.root_id, data=self.data)
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsCleanupStopCollector"),
                file_list=[],
                bk_host_list=host_list,
                exec_account="root",
                script_content=cleanup_dts_work_script(work_dir),
            )
        )
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsCleanupDropSourceUser"),
                file_list=[],
                bk_host_list=[{"ip": src.get_connect_node().ip, "bk_cloud_id": src.bk_cloud_id}],
                exec_account="root",
                script_content=self._drop_user_script(src, src_user),
            )
        )
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsCleanupDropTargetUser"),
                file_list=[],
                bk_host_list=[{"ip": dst.get_connect_node().ip, "bk_cloud_id": dst.bk_cloud_id}],
                exec_account="root",
                script_content=self._drop_user_script(dst, dst_user),
            )
        )
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsCleanupDropCkpt"),
                file_list=[],
                bk_host_list=[{"ip": dst.get_connect_node().ip, "bk_cloud_id": dst.bk_cloud_id}],
                exec_account="root",
                script_content=self._drop_ckpt_script(dst, collector_id),
            )
        )
        if recycle and job_host_id:
            add_job_host_destroy_acts(
                pipeline,
                JobHostDestroyInput(
                    root_id=self.root_id,
                    creator=self.data.get("created_by") or "",
                    job_host_id=job_host_id,
                    recycle_hosts=True,
                    only_if_created=False,
                    bk_biz_id=int(self.data.get("bk_biz_id") or src.bk_biz_id),
                ),
            )
        pipeline.run_pipeline(init_trans_data_class=JobHostTransData())

    @staticmethod
    def _source_addrs(cluster: MongoDBCluster, user: str, password: str, source_connect_mode: str):
        """
        source_connect_mode:
          - backup: 副本集只连 MONGO_BACKUP（hidden），mongo_connect_mode=standalone
          - secondaryPreferred: 连全部成员，mongo_connect_mode=secondaryPreferred
        分片集群走 mongos；backup 模式不适用。
        """
        if cluster.is_sharded_cluster():
            return resolve_source_connect(
                source_connect_mode,
                user,
                password,
                is_sharded=True,
                mongos_addrs=[node.addr() for node in cluster.get_mongos()],
                cluster_name=cluster.name,
            )
        shard = cluster.get_shards()[0]
        backup = shard.get_backup_node()
        return resolve_source_connect(
            source_connect_mode,
            user,
            password,
            is_sharded=False,
            member_addrs=[node.addr() for node in shard.members],
            backup_addr=backup.addr() if backup else None,
            cluster_name=cluster.name,
        )

    @staticmethod
    def _target_url(cluster: MongoDBCluster, user: str, password: str) -> str:
        if cluster.is_sharded_cluster():
            addrs = [node.addr() for node in cluster.get_mongos()]
        else:
            addrs = [node.addr() for node in cluster.get_shards()[0].members]
        return mongo_uri(user, password, addrs)

    @staticmethod
    def _admin_connect_uri(cluster: MongoDBCluster) -> str:
        if cluster.is_sharded_cluster():
            return ""
        shard = cluster.get_shards()[0]
        addrs = [node.addr() for node in shard.members]
        return replica_set_connect_uri(addrs, shard.set_name or cluster.name)

    @staticmethod
    def _user_script(cluster: MongoDBCluster, user: str, password: str, roles_js: str) -> str:
        node = cluster.get_connect_node()
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        return create_user_script(
            node.ip,
            node.port,
            dba_user,
            dba_pwd,
            user,
            password,
            roles_js,
            connect_uri=MongoDBDtsFlow._admin_connect_uri(cluster),
        )

    @staticmethod
    def _check_empty_script(cluster: MongoDBCluster) -> str:
        node = cluster.get_connect_node()
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        return check_empty_target_script(
            node.ip,
            node.port,
            dba_user,
            dba_pwd,
            connect_uri=MongoDBDtsFlow._admin_connect_uri(cluster),
        )

    @staticmethod
    def _assert_sharded_script(cluster: MongoDBCluster) -> str:
        node = cluster.get_connect_node()
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        return assert_target_user_collections_sharded_script(
            node.ip,
            node.port,
            dba_user,
            dba_pwd,
            connect_uri=MongoDBDtsFlow._admin_connect_uri(cluster),
        )

    @staticmethod
    def _drop_ckpt_script(cluster: MongoDBCluster, collector_id: str) -> str:
        node = cluster.get_connect_node()
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        return drop_mongoshake_ckpt_script(
            node.ip,
            node.port,
            dba_user,
            dba_pwd,
            collector_id,
            connect_uri=MongoDBDtsFlow._admin_connect_uri(cluster),
        )

    @staticmethod
    def _drop_user_script(cluster: MongoDBCluster, user: str) -> str:
        node = cluster.get_connect_node()
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        return drop_user_script(
            node.ip,
            node.port,
            dba_user,
            dba_pwd,
            user,
            connect_uri=MongoDBDtsFlow._admin_connect_uri(cluster),
        )
