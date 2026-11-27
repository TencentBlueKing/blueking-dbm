# -*- coding: utf-8 -*-
"""
MongoDB DTS。MongoShake collector 跑在执行机上，追平后停掉并回收。

ExecHost 三种来源：单据资源申请节点按规格申请并回填的主机、手填的业务空闲机（都在 infos[].exec_host），
或复用已有执行机 infos[].exec_host_id。结束时释放引用，无其它流程引用且需回收时下架，
并写入单据 recycle_hosts，单据成功后走标准主机回收单。
介质 pkg_type=mongo-dts（mongo-dts.tar.gz，包内 collector.linux），下发到 /data/mongo-dts/install/。
collector 的启动、等待追平、追平停止、手动停止都由 mongo-dbactuator 原子任务 mongoshake_collector 执行。
人工确认模式先等到追平（collector 继续跑），确认后再停。
"""

import logging
import re
import secrets
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.models import Machine
from backend.exec_host.models import ExecHost, ExecHostStatus
from backend.flow.consts import FAILED_STATES, MediumEnum, MongoDBActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mongodb.base_flow import MongoBaseFlow
from backend.flow.engine.bamboo.scene.mongodb.sub_task.exec_shell_script import ExecShellScript
from backend.flow.engine.bamboo.scene.mongodb.sub_task.send_media import SendMedia
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mongodb.exec_actuator_job2 import ExecJobComponent2
from backend.flow.plugins.components.collections.mongodb.mongo_dts_marker import (
    MONGO_DTS_COMPONENT_CODE,
    MongoDtsMarkerComponent,
)
from backend.flow.utils.exec_host import (
    ExecHostDestroyInput,
    ExecHostEnsureInput,
    ExecHostTransData,
    add_exec_host_destroy_acts,
    add_exec_host_ensure_acts,
    resolve_exec_host_from_row,
)
from backend.flow.utils.exec_host.ensure import EXEC_HOST_REGISTER_META, EXEC_HOST_RESOLVE_META
from backend.flow.utils.exec_host.lease import DTS_ROOT_ID_TAG, DTS_ROOT_IDS_TAG, root_ids_from_tags
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext
from backend.flow.utils.mongodb.mongodb_repo import MongoDBCluster, MongoRepository
from backend.flow.utils.mongodb.mongodb_util import MongoUtil
from backend.flow.utils.mongodb.mongoshake_conf import (
    CATCHUP_LAG_SECONDS,
    CATCHUP_POLL_SECONDS,
    CATCHUP_STABLE_ROUNDS,
    STOP_MODE_MANUAL,
    assert_balancer_stopped_script,
    assert_mongoshake_supported_version,
    assert_target_user_collections_sharded_script,
    build_collector_conf,
    check_empty_target_script,
    collector_http_ports,
    create_user_script,
    drop_mongoshake_ckpt_script,
    drop_user_script,
    mongo_dts_pkg_path,
    mongo_uri,
    namespace_list,
    normalize_source_connect_mode,
    normalize_stop_mode,
    replica_set_connect_uri,
    resolve_source_connect,
)
from backend.flow.utils.mongodb.version_utils import compare_mongodb_versions, get_mongodb_package_v2_release

logger = logging.getLogger("flow")

# readAnyDatabase 不含 local/config；MongoShake 取位点会读 local，列举集合会碰 config。
SOURCE_ROLES = (
    '[{role:"readAnyDatabase",db:"admin"},'
    '{role:"read",db:"local"},{role:"read",db:"config"},{role:"read",db:"admin"},'
    '{role:"clusterMonitor",db:"admin"}]'
)
TARGET_ROLES = '[{role:"readWriteAnyDatabase",db:"admin"},{role:"clusterManager",db:"admin"}]'
EXEC_HOST_PURPOSE = "mongoshake_dts"
EXEC_HOST_DEPLOY_PATH = "/data/mongo-dts"
_WORK_DIR_RE = re.compile(r"^/data/mongo-dts/mongodts[A-Za-z0-9]{1,12}$")
_TEMP_USER_RE = re.compile(r"^mongodts_(src|dst)_[A-Za-z0-9]{1,12}$")
_SOURCE_ROOT_ID_RE = re.compile(r"^[0-9a-f]{14}$")
# Legacy trees (before mongo_dts marker): ExecHost ensure codes used only by DTS today.
_LEGACY_DTS_COMPONENT_CODES = (EXEC_HOST_REGISTER_META, EXEC_HOST_RESOLVE_META)
_ACTIVE_EXEC_HOST = (ExecHostStatus.DEPLOYING.value, ExecHostStatus.RUNNING.value)


class MongoDBDtsFlow(object):
    """在执行机上跑 MongoShake，追平后停掉 collector、删临时账号并按需销毁执行机。"""

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
        work_dir = "{}/{}".format(EXEC_HOST_DEPLOY_PATH, collector_id)
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

    def _actuator_workdir(self) -> str:
        file_path = MongoUtil().get_mongodb_os_conf()["file_path"]
        if not file_path or file_path == "/":
            raise Exception("mongodb file_path is empty")
        return file_path

    def _send_actuator(self, pipeline, host_list):
        pipeline.add_act(
            **SendMedia.act(
                act_name=_("MG-DtsSendActuator"),
                file_list=GetFileList(db_type=DBType.MongoDB).get_db_actuator_package(),
                bk_host_list=host_list,
                file_target_path=self._actuator_workdir(),
            )
        )

    def _add_collector_act(self, pipeline, act_name, exec_ip, bk_cloud_id, payload):
        pipeline.add_act(
            act_name=act_name,
            act_component_code=ExecJobComponent2.code,
            kwargs={
                "set_trans_data_dataclass": CommonContext.__name__,
                "get_trans_data_ip_var": None,
                "bk_cloud_id": bk_cloud_id,
                "exec_ip": exec_ip,
                "db_act_template": {
                    "action": MongoDBActuatorActionEnum.MongoShakeCollector,
                    "file_path": self._actuator_workdir(),
                    "exec_account": "root",
                    "sudo_account": "root",
                    "payload": payload,
                },
            },
        )

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
        # MongoShake 不会 shardCollection。是否已分片默认不检查，require_target_sharded 为真时才校验。

        exec_host_id, exec_host_ip = resolve_exec_host_from_row(row, src.bk_cloud_id)
        ident = self.dts_task_identity(self.root_id)
        token = ident["token"]
        collector_id = ident["collector_id"]
        work_dir = ident["work_dir"]
        exec_host_name = row.get("exec_host_name") or "mongodts-{}".format(token)
        src_user, src_pwd = ident["src_user"], secrets.token_hex(16)
        dst_user, dst_pwd = ident["dst_user"], secrets.token_hex(16)
        source_connect_mode = normalize_source_connect_mode(row.get("source_connect_mode"))
        stop_mode = normalize_stop_mode(row.get("stop_mode"))
        source_urls, source_mongos, source_config, mongo_connect_mode = self._source_addrs(
            src, src_user, src_pwd, source_connect_mode
        )
        target_url = self._target_url(dst, dst_user, dst_pwd)
        full_port, incr_port = collector_http_ports(collector_id)
        conf = build_collector_conf(
            collector_id=collector_id,
            log_dir="{}/logs".format(work_dir),
            source_urls=source_urls,
            source_mongos_url=source_mongos,
            source_config_url=source_config,
            target_url=target_url,
            namespace_white=namespace_list(row.get("namespaces") or []),
            transform_namespace=row.get("transform_namespace") or "",
            full_http_port=full_port,
            incr_http_port=incr_port,
            mongo_connect_mode=mongo_connect_mode,
            filter_orphan_document=src.is_sharded_cluster(),
            do_not_shard_destination=src.is_sharded_cluster() and (not dst.is_sharded_cluster()),
        )
        dts_pkg = get_mongodb_package_v2_release(MediumEnum.MongoDts.value)
        dts_file = "{}/{}/{}".format(env.BKREPO_PROJECT, env.BKREPO_BUCKET, dts_pkg.path)
        recycle = row.get("recycle_exec_host", True)
        logger.info(
            "MongoDBDtsFlow collector=%s exec_host=%s pkg=%s recycle=%s",
            collector_id,
            exec_host_ip or "id:{}".format(exec_host_id),
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
        if not exec_host_id:
            send_media_act = SendMedia.act(
                act_name=_("MG-DtsSendMongoDts"),
                file_list=[dts_file],
                bk_host_list=[{"ip": exec_host_ip, "bk_cloud_id": src.bk_cloud_id}],
                file_target_path=EXEC_HOST_DEPLOY_PATH,
            )
        # 复用执行机时，加载节点在流程内登记本 root_id 引用（供清理校验与回收计数）。
        add_exec_host_ensure_acts(
            pipeline,
            ExecHostEnsureInput(
                root_id=self.root_id,
                bk_biz_id=int(self.data.get("bk_biz_id") or src.bk_biz_id),
                bk_cloud_id=src.bk_cloud_id,
                name=exec_host_name,
                ip=exec_host_ip,
                exec_host_id=exec_host_id,
                deploy_path=EXEC_HOST_DEPLOY_PATH,
                version=dts_pkg.name,
                db_type=DBType.MongoDB.value,
                purpose=EXEC_HOST_PURPOSE,
                tags={DTS_ROOT_ID_TAG: self.root_id, DTS_ROOT_IDS_TAG: [self.root_id]},
                creator=self.data.get("created_by") or "",
                send_media_act=send_media_act,
            ),
        )
        # 脚本执行机：新建用 ticket IP；复用时 ensure 已校验，仍用库中 IP
        exec_ip = exec_host_ip
        if exec_host_id and not exec_ip:
            exec_ip = ExecHost.objects.get(id=exec_host_id).ip
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
        # 默认不检查目标是否已 shardCollection；单据 require_target_sharded=true 时才强制。
        if dst.is_sharded_cluster() and row.get("require_target_sharded"):
            pipeline.add_act(
                **ExecShellScript.act(
                    act_name=_("MG-DtsCheckTargetSharded"),
                    file_list=[],
                    bk_host_list=[{"ip": dst.get_connect_node().ip, "bk_cloud_id": dst.bk_cloud_id}],
                    exec_account="root",
                    script_content=self._assert_sharded_script(dst),
                )
            )
        if src.is_sharded_cluster():
            balancer_node, balancer_script = self._balancer_check(src)
            pipeline.add_act(
                **ExecShellScript.act(
                    act_name=_("MG-DtsCheckBalancerStopped"),
                    file_list=[],
                    bk_host_list=[{"ip": balancer_node.ip, "bk_cloud_id": balancer_node.bk_cloud_id}],
                    exec_account="root",
                    script_content=balancer_script,
                )
            )
        for source_node, source_script in self._source_user_scripts(src, src_user, src_pwd, SOURCE_ROLES):
            pipeline.add_act(
                **ExecShellScript.act(
                    act_name=_("MG-DtsCreateSourceUser"),
                    file_list=[],
                    bk_host_list=[{"ip": source_node.ip, "bk_cloud_id": source_node.bk_cloud_id}],
                    exec_account="root",
                    script_content=source_script,
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
        self._send_actuator(pipeline, host_list)
        self._add_collector_act(
            pipeline,
            _("MG-DtsStartMongoShake"),
            exec_ip,
            src.bk_cloud_id,
            {
                "op": "start",
                "workDir": work_dir,
                "pkgPath": mongo_dts_pkg_path(),
                "conf": conf,
            },
        )
        catchup_payload = {
            "op": "wait_stop",
            "workDir": work_dir,
            "fullHttpPort": full_port,
            "incrHttpPort": incr_port,
            "lagSeconds": CATCHUP_LAG_SECONDS,
            "stableRounds": CATCHUP_STABLE_ROUNDS,
            "pollSeconds": CATCHUP_POLL_SECONDS,
            "deadlineSeconds": 82800,
            "removeConf": True,
        }
        if stop_mode == STOP_MODE_MANUAL:
            # 先等到追平，collector 继续同步；确认后再停。确认前的新写入仍会跟上。
            self._add_collector_act(
                pipeline,
                _("MG-DtsWaitCatchup"),
                exec_ip,
                src.bk_cloud_id,
                dict(catchup_payload, op="wait", removeConf=False),
            )
            pipeline.add_act(
                act_name=_("MG-DtsManualStopConfirm"),
                act_component_code=PauseComponent.code,
                kwargs={
                    "description": _("MongoShake 已追平并仍在同步（全量端口 {} / 增量端口 {}）。确认后停止同步。").format(full_port, incr_port),
                },
            )
            self._add_collector_act(
                pipeline,
                _("MG-DtsStopMongoShake"),
                exec_ip,
                src.bk_cloud_id,
                catchup_payload,
            )
        else:
            self._add_collector_act(
                pipeline,
                _("MG-DtsWaitCatchupAndStop"),
                exec_ip,
                src.bk_cloud_id,
                catchup_payload,
            )
        # checkpoint 只在同步期间有用，留在目标上会让下一次迁移的目标空库检查失败。
        pipeline.add_act(
            **ExecShellScript.act(
                act_name=_("MG-DtsDropCkpt"),
                file_list=[],
                bk_host_list=[{"ip": dst.get_connect_node().ip, "bk_cloud_id": dst.bk_cloud_id}],
                exec_account="root",
                script_content=self._drop_ckpt_script(dst, collector_id),
            )
        )
        for source_node, source_script in self._drop_source_user_scripts(src, src_user):
            pipeline.add_act(
                **ExecShellScript.act(
                    act_name=_("MG-DtsDropSourceUser"),
                    file_list=[],
                    bk_host_list=[{"ip": source_node.ip, "bk_cloud_id": source_node.bk_cloud_id}],
                    exec_account="root",
                    script_content=source_script,
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
        # 无论是否回收，都要释放本流程引用。仍有其它流程持有时不回收。
        add_exec_host_destroy_acts(
            pipeline,
            ExecHostDestroyInput(
                root_id=self.root_id,
                creator=self.data.get("created_by") or "",
                exec_host_id=exec_host_id,
                recycle_hosts=bool(recycle),
                only_if_created=False,
                bk_biz_id=int(self.data.get("bk_biz_id") or src.bk_biz_id),
                ticket_id=int(self.data.get("uid") or 0),
            ),
        )
        pipeline.run_pipeline(init_trans_data_class=ExecHostTransData())

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
        """Identify DTS by marker component code; fall back to ExecHost ensure codes for legacy trees."""
        if cls.tree_has_component(tree_data, MONGO_DTS_COMPONENT_CODE):
            return True
        return any(cls.tree_has_component(tree_data, code) for code in _LEGACY_DTS_COMPONENT_CODES)

    @classmethod
    def assert_exec_host_bound_to_dts(cls, exec_host_id: int, source_root_id: str) -> None:
        """Cleanup exec_host_id must belong to the failed DTS flow (tag or runtime hosts)."""
        job = ExecHost.objects.filter(id=exec_host_id).first()
        if not job:
            raise Exception(_("执行机 id={} 不存在").format(exec_host_id))
        if source_root_id in root_ids_from_tags(job.tags):
            return
        if cls.flow_used_ip(source_root_id, job.ip):
            return
        raise Exception("exec_host_id={} is not bound to DTS source_root_id={}".format(exec_host_id, source_root_id))

    @staticmethod
    def flow_used_ip(root_id: str, ip: str) -> bool:
        for node in FlowNode.objects.filter(root_id=root_id).only("hosts"):
            for host in node.hosts or []:
                host_ip = host if isinstance(host, str) else (host or {}).get("ip")
                if host_ip and host_ip == ip:
                    return True
        return False

    @staticmethod
    def _bound_exec_host_id_by_ip(ip: str, bk_cloud_id: int, root_id: str) -> Optional[int]:
        """只传 IP 清理时，找出失败流程登记过的活跃执行机，按执行机走释放与回收。"""
        for job in ExecHost.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id, status__in=_ACTIVE_EXEC_HOST):
            if root_id in root_ids_from_tags(job.tags):
                return job.id
        return None

    def _recycle_unregistered_applied_host(self, failed_root_id: str, ip: str) -> None:
        """只回收失败单据资源申请得到的主机；手填的业务空闲机没有执行机记录时不动。"""
        from backend.db_services.dbresource.handlers import ResourceHandler
        from backend.ticket.models import Ticket

        tree = FlowTree.objects.filter(root_id=failed_root_id).first()
        failed_ticket = Ticket.objects.filter(id=int(tree.uid)).first() if tree and tree.uid else None
        if not failed_ticket:
            return
        nodes = failed_ticket.details.get("nodes") or {}
        host_ids = [
            node["bk_host_id"]
            for key, items in nodes.items()
            if key.endswith("_exec_host")
            for node in items or []
            if node.get("ip") == ip and node.get("bk_host_id")
        ]
        if not host_ids or Machine.objects.filter(bk_host_id__in=host_ids).exists():
            return
        ticket = Ticket.objects.get(id=int(self.data["uid"]))
        ticket.update_details(recycle_hosts=ResourceHandler.standardized_resource_host([{"bk_host_id": host_ids[0]}]))
        logger.info("MongoDBDtsFlow cleanup: recycle unregistered applied exec host %s", ip)

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
        Manual cleanup after a failed DTS run: stop collector, drop temp users / ckpt, optionally recycle ExecHost.

        work_dir / temp users are derived from the *failed* DTS root_id (source_root_id), never from
        this cleanup flow's own root_id.
        Expected ticket_data:
          source_root_id (or infos[0].source_root_id),
          infos[0].source_cluster_id, target_cluster_id,
          exec_host_id (optional), recycle_exec_host (default True),
          exec_host_ip (required when exec_host_id empty)
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
        exec_host_id, exec_host_ip = resolve_exec_host_from_row(row, src.bk_cloud_id)
        recycle = row.get("recycle_exec_host", True)
        if exec_host_id:
            self.assert_exec_host_bound_to_dts(int(exec_host_id), failed_root_id)
        elif not self.flow_used_ip(failed_root_id, exec_host_ip):
            # 只传 IP 时也必须是失败流程实际用过的执行机，不能在任意主机上以 root 执行。
            raise Exception(
                "exec_host ip={} was not used by DTS source_root_id={}".format(exec_host_ip, failed_root_id)
            )
        else:
            exec_host_id = self._bound_exec_host_id_by_ip(exec_host_ip, src.bk_cloud_id, failed_root_id)
            if not exec_host_id and recycle:
                # 失败在注册执行机之前：资源申请到的主机没有执行机记录，直接写入本单 recycle_hosts
                self._recycle_unregistered_applied_host(failed_root_id, exec_host_ip)
        exec_ip = exec_host_ip
        if exec_host_id and not exec_ip:
            exec_ip = ExecHost.objects.get(id=exec_host_id).ip
        if not exec_ip:
            raise Exception(_("清理时执行机 IP 不能为空"))
        host_list = [{"ip": exec_ip, "bk_cloud_id": src.bk_cloud_id}]

        pipeline = Builder(root_id=self.root_id, data=self.data)
        self._send_actuator(pipeline, host_list)
        self._add_collector_act(
            pipeline,
            _("MG-DtsCleanupStopCollector"),
            exec_ip,
            src.bk_cloud_id,
            {"op": "stop", "workDir": work_dir, "removeConf": True},
        )
        for source_node, source_script in self._drop_source_user_scripts(src, src_user):
            pipeline.add_act(
                **ExecShellScript.act(
                    act_name=_("MG-DtsCleanupDropSourceUser"),
                    file_list=[],
                    bk_host_list=[{"ip": source_node.ip, "bk_cloud_id": source_node.bk_cloud_id}],
                    exec_account="root",
                    script_content=source_script,
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
        if exec_host_id:
            add_exec_host_destroy_acts(
                pipeline,
                ExecHostDestroyInput(
                    root_id=failed_root_id,
                    creator=self.data.get("created_by") or "",
                    exec_host_id=exec_host_id,
                    recycle_hosts=bool(recycle),
                    only_if_created=False,
                    bk_biz_id=int(self.data.get("bk_biz_id") or src.bk_biz_id),
                    ticket_id=int(self.data.get("uid") or 0),
                ),
            )
        pipeline.run_pipeline(init_trans_data_class=ExecHostTransData())

    @staticmethod
    def _source_addrs(cluster: MongoDBCluster, user: str, password: str, source_connect_mode: str):
        """
        source_connect_mode:
          - backup: 副本集用 directConnection URI 只连 MONGO_BACKUP（hidden）
          - secondaryPreferred: 连全部成员，mongo_connect_mode=secondaryPreferred
        分片集群固定直连每个 shard/configsvr 的 MONGO_BACKUP。
        """
        if cluster.is_sharded_cluster():
            shard_backups = []
            shards = cluster.get_shards(with_config=False, sort_by_set_name=True)
            if len(shards) < 2:
                raise ValueError(
                    "MongoShake oplog mode requires at least two shards for sharded source {}".format(cluster.name)
                )
            for shard in shards:
                backup = shard.get_backup_node()
                if not backup:
                    raise ValueError(
                        "sharded source {} shard {} has no MONGO_BACKUP member".format(cluster.name, shard.set_name)
                    )
                shard_backups.append(backup.addr())
            config = cluster.get_config()
            if not config:
                raise ValueError("sharded source {} has no configsvr".format(cluster.name))
            config_backup = config.get_backup_node()
            if not config_backup:
                raise ValueError(
                    "sharded source {} configsvr {} has no MONGO_BACKUP member".format(cluster.name, config.set_name)
                )
            return resolve_source_connect(
                source_connect_mode,
                user,
                password,
                is_sharded=True,
                shard_backup_addrs=shard_backups,
                config_backup_addr=config_backup.addr(),
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
    def _replica_set_admin_targets(cluster: MongoDBCluster):
        replica_sets = (
            cluster.get_shards(with_config=True, sort_by_set_name=True)
            if cluster.is_sharded_cluster()
            else cluster.get_shards()
        )
        targets = []
        for replica_set in replica_sets:
            nodes = replica_set.get_not_backup_nodes()
            if not nodes:
                raise ValueError("replica set {} has no non-backup member".format(replica_set.set_name))
            node = nodes[0]
            uri = replica_set_connect_uri([member.addr() for member in replica_set.members], replica_set.set_name)
            targets.append((node, uri))
        return targets

    @classmethod
    def _source_user_scripts(cls, cluster: MongoDBCluster, user: str, password: str, roles_js: str):
        scripts = []
        for node, uri in cls._replica_set_admin_targets(cluster):
            dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
            scripts.append(
                (
                    node,
                    create_user_script(
                        node.ip,
                        node.port,
                        dba_user,
                        dba_pwd,
                        user,
                        password,
                        roles_js,
                        connect_uri=uri,
                    ),
                )
            )
        return scripts

    @classmethod
    def _drop_source_user_scripts(cls, cluster: MongoDBCluster, user: str):
        scripts = []
        for node, uri in cls._replica_set_admin_targets(cluster):
            dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
            scripts.append(
                (
                    node,
                    drop_user_script(node.ip, node.port, dba_user, dba_pwd, user, connect_uri=uri),
                )
            )
        return scripts

    @classmethod
    def _balancer_check(cls, cluster: MongoDBCluster):
        config = cluster.get_config()
        if not config:
            raise ValueError("sharded source {} has no configsvr".format(cluster.name))
        node, uri = cls._replica_set_admin_targets(cluster)[0]
        dba_user, dba_pwd = MongoUtil.get_dba_user_password(node.ip, node.port, node.bk_cloud_id)
        return node, assert_balancer_stopped_script(
            node.ip,
            node.port,
            dba_user,
            dba_pwd,
            connect_uri=uri,
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
