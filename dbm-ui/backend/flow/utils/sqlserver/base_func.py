"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.consts import DEFAULT_SQLSERVER_PORT


def calc_install_ports(inst_sum: int) -> list:
    """
    计算单据流程需要安装的端口，然后传入到流程的单据信息
    @param inst_sum: 代表机器部署实例数量
    """
    install_ports = []
    for i in range(0, inst_sum):
        install_ports.append(DEFAULT_SQLSERVER_PORT + i * 10)

    return install_ports
