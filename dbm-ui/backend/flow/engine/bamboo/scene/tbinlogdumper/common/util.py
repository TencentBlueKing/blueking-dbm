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
from backend.db_meta.models import Machine, StorageInstance
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.consts import TBINLOGDUMPER_PORT
from backend.flow.engine.bamboo.scene.tbinlogdumper.common.exceptions import TBinlogDumperFlowBaseException


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
                ExtraProcessInstance.objects.filter(machine=machine, listen_port=default_port).exists()
                or StorageInstance.objects.filter(machine=machine, port=default_port).exists()
            ):

                # 如果端口在元信息记录部署，则往上添加100
                default_port += 100

            else:
                break

        install_ports.append(default_port)
    if len(install_ports) != install_num:
        raise TBinlogDumperFlowBaseException(message=_("获取预安装端口失败"))

    return install_ports


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
        raise TBinlogDumperFlowBaseException(message=_("get charset failed: {}".format(res[0]["error_msg"])))

    table_data = res[0]["cmd_results"][0]["table_data"]
    return table_data[0]["Value"]
