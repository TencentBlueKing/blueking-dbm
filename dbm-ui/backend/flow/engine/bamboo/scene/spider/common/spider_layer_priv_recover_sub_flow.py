# -*- coding: utf-8 -*-
"""
TenDBCluster 接入层：从 Spider/tdbctl grant 备份恢复权限到指定机器与端口（非 HA storage 维度）。
"""
import copy
import logging
from dataclasses import asdict

from django.utils.translation import gettext as _

from backend.configuration.constants import MYSQL_USUAL_JOB_TIME
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.mysql_restore_download_sub_flow import (
    mysql_restore_download_sub_flow,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.mysql.mysql_act_dataclass import ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


def spider_layer_priv_recover_sub_flow(
    root_id: str,
    uid: str,
    ticket_data: dict,
    cluster_model,
    restore_ips: list,
    backup_info: dict,
    restore_port: int,
):
    """
    下载 grant SQL 并在 restore_ips 上按 restore_port 执行 tendb_restore_priv_payload。
    """
    if not backup_info or not backup_info.get("priv_files"):
        return None
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    priv_sub_pipeline_list = []
    for restore_ip in restore_ips:
        cluster_ctx = {
            "cluster_id": cluster_model.id,
            "file_target_path": "/data/dbbak/{}/{}/restore_priv".format(root_id, restore_port),
            "sql_files": backup_info["priv_files"],
            "port": restore_port,
            "force": False,
        }
        sub_pipeline.add_sub_pipeline(
            sub_flow=mysql_restore_download_sub_flow(
                root_id=root_id,
                uid=uid,
                bk_cloud_id=cluster_model.bk_cloud_id,
                file_target_path=cluster_ctx["file_target_path"],
                task_ids=backup_info["task_ids"],
                dest_ips=[restore_ip],
                source_ip=None,
            )
        )
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=cluster_model.bk_cloud_id,
            cluster_type=cluster_model.cluster_type,
            cluster=copy.deepcopy(cluster_ctx),
            job_timeout=MYSQL_USUAL_JOB_TIME,
            get_mysql_payload_func=MysqlActPayload.tendb_restore_priv_payload.__name__,
            exec_ip=restore_ip,
        )
        priv_sub = SubBuilder(root_id=root_id, data=ticket_data)
        priv_sub.add_act(
            act_name=_("{}:{} 接入层权限恢复 backup_ids: {}").format(
                restore_ip, restore_port, backup_info.get("backup_ids", [])
            ),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        priv_sub_pipeline_list.append(priv_sub.build_sub_process(sub_name=_("{} 权限恢复").format(restore_ip)))
    if priv_sub_pipeline_list:
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=priv_sub_pipeline_list)
        return sub_pipeline.build_sub_process(sub_name=_("集群 {} Spider 接入层权限恢复").format(cluster_model.id))
    return None
