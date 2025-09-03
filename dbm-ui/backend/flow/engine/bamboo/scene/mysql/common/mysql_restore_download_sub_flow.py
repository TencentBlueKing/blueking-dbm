"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_download_backupfile import (
    MySQLDownloadBackupfileComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent as MySQLTransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DownloadBackupFileKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    P2PFileKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def mysql_restore_download_sub_flow(
    uid: str,
    root_id: str,
    bk_cloud_id: int,
    file_target_path: str,
    task_ids: list[str],
    dest_ips: list[str],
    source_ip: str = None,
):
    """
    定义 mysql 恢复下载备份文件子流程
    @param uid:  flow流程的uid
    @param root_id:  flow流程的root_id
    @param bk_cloud_id:  云区域ID
    @param file_target_path:  备份文件目标路径
    @param task_ids:  备份文件任务ID
    @param dest_ips:  目标IP
    @param source_ip:  源IP,如果源ip为None,表示从远程下载。
    @return:  子流程
    """
    ticket_data = {
        "uid": uid,
        "root_id": root_id,
        "bk_cloud_id": bk_cloud_id,
        "file_target_path": file_target_path,
        "task_ids": task_ids,
        "dest_ips": dest_ips,
        "source_ip": source_ip,
    }
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=bk_cloud_id,
        cluster=ticket_data,
        exec_ip=dest_ips,
        get_mysql_payload_func=MysqlActPayload.mysql_mkdir_dir.__name__,
    )
    sub_pipeline.add_act(
        act_name=_("创建目录 {}".format(ticket_data["file_target_path"])),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )

    if source_ip is None:
        # 从远程下载备份文件
        download_sub_pipeline_list = []
        for dest_ip in dest_ips:
            download_kwargs = DownloadBackupFileKwargs(
                bk_cloud_id=bk_cloud_id,
                task_ids=task_ids,
                dest_ip=dest_ip,
                dest_dir=file_target_path,
                reason="download from remote backup system",
            )
            download_sub_pipeline_list.append(
                {
                    "act_name": _("远程备份文件到 {}".format(dest_ip)),
                    "act_component_code": MySQLDownloadBackupfileComponent.code,
                    "kwargs": asdict(download_kwargs),
                }
            )
        sub_pipeline.add_parallel_acts(download_sub_pipeline_list)
    else:
        # 点对点传输备份文件
        sub_pipeline.add_act(
            act_name=_("下发db-actor到节点"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=dest_ips,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )
        sub_pipeline.add_act(
            act_name=_("从本地 {} 点对点传输文件到 {}").format(source_ip, dest_ips),
            act_component_code=MySQLTransFileComponent.code,
            kwargs=asdict(
                P2PFileKwargs(
                    bk_cloud_id=bk_cloud_id,
                    file_list=task_ids,
                    file_target_path=file_target_path,
                    source_ip_list=[source_ip],
                    exec_ip=dest_ips,
                )
            ),
        )
    return sub_pipeline.build_sub_process(sub_name=_("下载备份文件"))
