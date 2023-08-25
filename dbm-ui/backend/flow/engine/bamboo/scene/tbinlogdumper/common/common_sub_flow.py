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
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.util import get_tbinlogdumper_charset
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

"""
定义一些TBinlogDumper流程上可能会用到的子流程，以便于减少代码的重复率
"""


def add_tbinlogdumper_sub_flow(
    cluster: Cluster,
    root_id: str,
    uid: str,
    add_conf_list: list,
    created_by: str = "",
):
    """
    定义对原有的TenDB cluster集群添加spider slave节点的公共子流程
    提供部分需要单据使用：比如添加从集群、扩容接入层等功能
    @param cluster: 待操作的集群
    @param uid: 单据uid
    @param root_id: flow流程的root_id
    @param add_conf_list: 本次上架的配置列表，每个的元素的格式为：{"module_id":x,"area_name":x,add_type:x}
    @param created_by: 单据发起者
    """
    # 查找集群的当前master实例, tendb-ha架构无论什么时候只有一个master角色
    master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)

    # 获取TBinlogDumper的字符集配置，以mysql数据源的为准
    charset = get_tbinlogdumper_charset(ip=master.machine.ip, port=master.port, bk_cloud_id=cluster.bk_cloud_id)

    parent_global_data = {
        "uid": uid,
        "add_conf_list": add_conf_list,
        "bk_biz_id": cluster.bk_biz_id,
        "created_by": created_by,
        "charset": charset,
    }
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    # 阶段1 并行分发安装文件
    sub_pipeline.add_act(
        act_name=_("下发TBinlogDumper介质包"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=master.machine.ip,
                file_list=GetFileList(db_type=DBType.MySQL).get_tbinlogdumper_package(),
            )
        ),
    )

    # 阶段2 并发安装TBinlogDumper实例
    sub_pipeline.add_act(
        act_name=_("安装TBinlogDumper实例"),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(
            ExecActuatorKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                cluster_type=cluster.cluster_type,
                exec_ip=master.machine.ip,
                get_mysql_payload_func=MysqlActPayload.install_tbinlogdumper_payload.__name__,
            )
        ),
    )

    return sub_pipeline.build_sub_process(sub_name=_("安装TBinlogDumper实例flow"))
