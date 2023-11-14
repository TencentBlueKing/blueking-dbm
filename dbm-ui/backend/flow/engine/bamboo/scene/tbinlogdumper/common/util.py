"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, Machine, StorageInstance
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.consts import TBINLOGDUMPER_PORT
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import NormalTBinlogDumperFlowException


def get_tbinlogdumper_install_port(machine: Machine, install_num: int) -> list:
    """
    根据ip以及当前部署的实例数量，返回预安装的端口列表
    """
    install_ports = []
    max_port = 40000
    default_port = TBINLOGDUMPER_PORT
    for i in range(0, install_num):
        while default_port <= max_port:
            if (
                ExtraProcessInstance.objects.filter(
                    bk_cloud_id=machine.bk_cloud_id, ip=machine.ip, listen_port=default_port
                ).exists()
                or StorageInstance.objects.filter(machine=machine, port=default_port).exists()
            ):

                # 如果端口在元信息记录部署，则往上添加100
                default_port += 100

            else:
                break

        if default_port <= max_port:
            install_ports.append(default_port)
            default_port += 100

    if len(install_ports) != install_num:
        raise NormalTBinlogDumperFlowException(
            message=_("获取预安装端口失败, 期望生成端口数:{}，实际生成端口数:{}".format(install_num, len(install_ports)))
        )

    return list(set(install_ports))


def get_tbinlogdumper_charset(ip: str, port: int, bk_cloud_id: int) -> str:
    """
    根据传进来的ip:port, 查询实例对应字符集配置
    """

    res = DRSApi.rpc(
        {
            "addresses": [f"{ip}{IP_PORT_DIVIDER}{port}"],
            "cmds": ["show global variables like 'character_set_server'"],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        raise NormalTBinlogDumperFlowException(message=_("get charset failed: {}".format(res[0]["error_msg"])))

    table_data = res[0]["cmd_results"][0]["table_data"]
    return table_data[0]["Value"]


def get_cluster(cluster_id: int, bk_biz_id: int) -> Cluster:
    """
    根据传入的clsuter_id 和 业务id，判断是否是HA类型集群
    如果是则返回cluster对象
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
    except Cluster.DoesNotExist:
        raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))
    if cluster.cluster_type != ClusterType.TenDBHA:
        raise NormalTBinlogDumperFlowException(message=_("非TenDB-HA架构不支持添加TBinlogDumper实例"))

    return cluster


def get_tbinlogdumper_server_id(master: StorageInstance, tbinlogdumper_port: int) -> int:
    """
    根据数据源的serverid，和tbinlogdumper端口号，计算出对应serverid
    确保主从同步是serverid不一致
    """
    res = DRSApi.rpc(
        {
            "addresses": [master.ip_port],
            "cmds": ["select @@server_id as id ;"],
            "force": False,
            "bk_cloud_id": master.machine.bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        raise NormalTBinlogDumperFlowException(message=_("get server_id failed: {}".format(res[0]["error_msg"])))

    master_server_id = res[0]["cmd_results"][0]["table_data"][0]["id"]
    return int(master_server_id) + tbinlogdumper_port
