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
from dataclasses import asdict
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend import env
from backend.core.consts import BK_PKG_INSTALL_PATH
from backend.flow.consts import ExecuteShellScriptUser
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.common.probe_exec_shell_script import ProbeExecuteShellScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs

# 探针介质包统一下发到 /data/install，解压后目录为 /home/mysql/dbha-v2
_PROBE_INSTALL_DIR = BK_PKG_INSTALL_PATH
_HOME_MYSQL_DIR = "/home/mysql"
_PROBE_DIR = f"{_HOME_MYSQL_DIR}/dbha-v2"


def probe_install_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
) -> SubProcess:
    """
    探针安装子流程包含：下发介质包 + 解压到目标目录。
    当 ENABLE_DBHA_V2=False 时禁用该子流程，需要在调用处也增加该校验。

    :param root_id: 流程 root_id
    :param data: global_data
    :param bk_cloud_id: 云区域 ID
    :param ips: 需要安装探针的机器 IP 列表
    """
    if not env.ENABLE_DBHA_V2:
        return

    sp = SubBuilder(root_id=root_id, data=data)

    probe_file_list, probe_pkg_name = GetFileList.get_dbha_v2_probe_package()

    # 下发探针介质包到目标机器 /data/install/
    sp.add_act(
        act_name=_("下发探针介质包"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=bk_cloud_id,
                exec_ip=ips,
                file_list=probe_file_list,
            )
        ),
    )

    # 解压介质包到 /home/mysql/dbha-v2
    install_script = f"""#!/bin/bash
set -e

INSTALL_DIR="{_PROBE_INSTALL_DIR}"
PROBE_PACKAGE="${{INSTALL_DIR}}"'/{probe_pkg_name}'

if [ ! -f "$PROBE_PACKAGE" ]; then
    echo "ERROR: probe package not found: $PROBE_PACKAGE"
    exit 1
fi

if [ -d "{_PROBE_DIR}" ]; then
    echo "Removing existing probe directory: {_PROBE_DIR}"
    rm -rf "{_PROBE_DIR}"
fi

mkdir -p "{_PROBE_DIR}"

tar -xzf "$PROBE_PACKAGE" -C "{_PROBE_DIR}" --strip-components=1

if [ ! -d "{_PROBE_DIR}" ]; then
    echo "ERROR: Probe directory not found after extraction: {_PROBE_DIR}"
    exit 1
fi

echo "probe package extracted to {_PROBE_DIR}"
"""

    sp.add_act(
        act_name=_("解压探针介质包"),
        act_component_code=ExecuteShellScriptComponent.code,
        kwargs={
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": ips,
            "cluster": {"shell_command": install_script},
            "account_alias": ExecuteShellScriptUser.Mysql.value,
        },
    )

    return sp.build_sub_process(sub_name=_("探针安装"))


def probe_start_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
) -> SubProcess:
    """
    探针启动子流程包含：生成配置文件 + 启动探针 + 检查探针健康状态。
    当 ENABLE_DBHA_V2=False 时禁用该子流程，需要在调用处也增加该校验。

    :param root_id: 流程 root_id
    :param data: global_data
    :param bk_cloud_id: 云区域 ID
    :param ips: 需要启动探针的机器 IP 列表
    """
    if not env.ENABLE_DBHA_V2:
        return

    sp = SubBuilder(root_id=root_id, data=data)

    # 启动探针，ADMIN_ENDPOINTS 由探针专属执行组件(ProbeExecuteShellScriptComponent)
    # 在运行时动态查询并替换，避免部署流程较长导致编排期固化的端点过期
    start_script = f"""#!/bin/bash
set -e

if [ ! -d "{_PROBE_DIR}" ]; then
    echo "probe not deployed on this host, skip start"
    exit 0
fi

cd "{_PROBE_DIR}"

./bin/dbha-probe gen-config --admin-endpoints '${{ADMIN_ENDPOINTS}}' -o etc/probe.yaml

./start-probe.sh

./bin/dbha-probe health
ps -ef | grep dbha-probe
"""

    sp.add_act(
        act_name=_("生成配置并启动探针"),
        act_component_code=ProbeExecuteShellScriptComponent.code,
        kwargs={
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": ips,
            "cluster": {"shell_command": start_script},
            "account_alias": ExecuteShellScriptUser.Mysql.value,
        },
    )

    return sp.build_sub_process(sub_name=_("探针启动"))


def probe_restart_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
) -> SubProcess:
    """
    探针重启子流程包含：停止探针 + 启动探针 + 检查探针健康状态。
    当 ENABLE_DBHA_V2=False 时禁用该子流程，需要在调用处也增加该校验。

    :param root_id: 流程 root_id
    :param data: global_data
    :param bk_cloud_id: 云区域 ID
    :param ips: 需要重启探针的机器 IP 列表
    """
    if not env.ENABLE_DBHA_V2:
        return

    sp = SubBuilder(root_id=root_id, data=data)

    # 重启探针
    restart_script = f"""#!/bin/bash
set -e

if [ ! -d "{_PROBE_DIR}" ]; then
    echo "probe not deployed on this host, skip restart"
    exit 0
fi

cd "{_PROBE_DIR}"

./stop-probe.sh

./start-probe.sh

./bin/dbha-probe health
ps -ef | grep dbha-probe
"""

    sp.add_act(
        act_name=_("停止探针并再启动探针"),
        act_component_code=ExecuteShellScriptComponent.code,
        kwargs={
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": ips,
            "cluster": {"shell_command": restart_script},
            "account_alias": ExecuteShellScriptUser.Mysql.value,
        },
    )

    return sp.build_sub_process(sub_name=_("探针重启"))


def probe_stop_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
) -> SubProcess:
    """
    探针停止子流程包含：停止探针进程 + 检查探针健康状态。
    当 ENABLE_DBHA_V2=False 时禁用该子流程，需要在调用处也增加该校验。

    :param root_id: 流程 root_id
    :param data: global_data
    :param bk_cloud_id: 云区域 ID
    :param ips: 需要停止探针的机器 IP 列表
    """
    if not env.ENABLE_DBHA_V2:
        return

    sp = SubBuilder(root_id=root_id, data=data)

    # 停止探针
    stop_script = f"""#!/bin/bash
set -e

if [ ! -d "{_PROBE_DIR}" ]; then
    echo "probe not deployed on this host, skip stop"
    exit 0
fi

cd "{_PROBE_DIR}"

./stop-probe.sh

./bin/dbha-probe health
ps -ef | grep dbha-probe
"""

    sp.add_act(
        act_name=_("停止探针进程"),
        act_component_code=ExecuteShellScriptComponent.code,
        kwargs={
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": ips,
            "cluster": {"shell_command": stop_script},
            "account_alias": ExecuteShellScriptUser.Mysql.value,
        },
    )

    return sp.build_sub_process(sub_name=_("探针停止"))


def probe_remove_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
) -> SubProcess:
    """
    探针目录清理子流程：删除探针安装目录，删除一并下发到 /data/install 的介质包。
    仅清理探针相关文件，不影响其它业务目录。
    当 ENABLE_DBHA_V2=False 时禁用该子流程。

    :param root_id: 流程 root_id
    :param data: global_data
    :param bk_cloud_id: 云区域 ID
    :param ips: 需要清理探针目录的机器 IP 列表
    """
    if not env.ENABLE_DBHA_V2:
        return

    sp = SubBuilder(root_id=root_id, data=data)

    remove_script = f"""#!/bin/bash
set -e

if [ -d "{_PROBE_DIR}" ]; then
    echo "Removing probe directory: {_PROBE_DIR}"
    rm -rf "{_PROBE_DIR}"
else
    echo "probe directory not found, skip remove: {_PROBE_DIR}"
fi

if [ -d "{_PROBE_INSTALL_DIR}" ]; then
    echo "Removing probe packages under: {_PROBE_INSTALL_DIR}"
    rm -f "{_PROBE_INSTALL_DIR}"/*-probe.tar.gz
else
    echo "install directory not found, skip remove: {_PROBE_INSTALL_DIR}"
fi

echo "probe directory cleared"
"""

    sp.add_act(
        act_name=_("清理探针目录及介质包"),
        act_component_code=ExecuteShellScriptComponent.code,
        kwargs={
            "bk_cloud_id": bk_cloud_id,
            "exec_ip": ips,
            "cluster": {"shell_command": remove_script},
            "account_alias": ExecuteShellScriptUser.Mysql.value,
        },
    )

    return sp.build_sub_process(sub_name=_("探针目录清理"))


def probe_upgrade_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
) -> SubProcess:
    """
    探针升级合成子流程：stop + install + start。
    用于在标准化集群子流程等场景中，一次性完成停止探针+最新介质包下发解压+启动探针。
    当 ENABLE_DBHA_V2=False 时禁用该子流程，需要在调用处也增加该校验。

    :param root_id: 流程 root_id
    :param data: 流程全局数据（global_data）
    :param bk_cloud_id: 云区域 ID
    :param ips: 需要升级探针的机器 IP 列表
    """
    if not env.ENABLE_DBHA_V2:
        return

    sp = SubBuilder(root_id=root_id, data=data)

    # 停止旧探针
    sp.add_sub_pipeline(
        sub_flow=probe_stop_sub_flow(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            ips=ips,
        )
    )

    # 安装最新介质包（下发 + 解压，解压前会对旧目录进行清理）
    sp.add_sub_pipeline(
        sub_flow=probe_install_sub_flow(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            ips=ips,
        )
    )

    # 启动探针（生成配置文件 + 启动探针 + 检查探针健康状态）
    sp.add_sub_pipeline(
        sub_flow=probe_start_sub_flow(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            ips=ips,
        )
    )

    return sp.build_sub_process(sub_name=_("探针升级"))


def deploy_probe_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
) -> SubProcess:
    """
    探针部署合成子流程：install + start。
    用于在标准化集群子流程等场景中，一次性完成介质包下发解压并启动探针。
    当 ENABLE_DBHA_V2=False 时禁用该子流程，需要在调用处也增加该校验。

    :param root_id: 流程 root_id
    :param data: global_data
    :param bk_cloud_id: 云区域 ID
    :param ips: 需要部署探针的机器 IP 列表
    """
    if not env.ENABLE_DBHA_V2:
        return

    sp = SubBuilder(root_id=root_id, data=data)

    # 安装探针
    sp.add_sub_pipeline(
        sub_flow=probe_install_sub_flow(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            ips=ips,
        )
    )

    # 启动探针
    sp.add_sub_pipeline(
        sub_flow=probe_start_sub_flow(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            ips=ips,
        )
    )

    return sp.build_sub_process(sub_name=_("探针部署"))


def probe_clean_sub_flow(
    root_id: str,
    data: Dict,
    bk_cloud_id: int,
    ips: List[str],
) -> SubProcess:
    """
    探针清理合成子流程：stop + remove。
    用于在标准化集群子流程等场景中，一次性完成停止探针+探针目录和介质包目录清理。
    当 ENABLE_DBHA_V2=False 时禁用该子流程，需要在调用处也增加该校验。

    :param root_id: 流程 root_id
    :param data: global_data
    :param bk_cloud_id: 云区域 ID
    :param ips: 需要清理探针的机器 IP 列表
    """
    if not env.ENABLE_DBHA_V2:
        return

    sp = SubBuilder(root_id=root_id, data=data)

    # 停止探针进程
    sp.add_sub_pipeline(
        sub_flow=probe_stop_sub_flow(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            ips=ips,
        )
    )

    # 清理探针目录与介质包
    sp.add_sub_pipeline(
        sub_flow=probe_remove_sub_flow(
            root_id=root_id,
            data=data,
            bk_cloud_id=bk_cloud_id,
            ips=ips,
        )
    )

    return sp.build_sub_process(sub_name=_("探针清理"))
