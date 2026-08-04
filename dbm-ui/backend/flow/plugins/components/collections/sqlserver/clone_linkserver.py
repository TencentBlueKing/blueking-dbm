# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQLServer LinkServer 克隆组件模块。

模块职责：
  - 从源实例读取全部 linked-server 元数据（名称、认证方式、远程登录名）
  - 对 use_self=False 的记录，从 DBM 授权中心按 remote_user 拉取明文密码，
    再用 AES-256-GCM 加密（key_seed = 目标实例 IP）
  - 将加密后的 linkserver_secrets 通过 component_kwargs 以显式命名参数注入
    get_clone_linkserver_payload，最终下发到目标实例，
    由 Go 端 dbactuator 使用相同 SALT 解密并克隆 linked-server

设计要点 / 数据源 / 通道：
  - 源实例元数据：DRSApi.sqlserver_rpc 直连源实例，查询 sys.servers + sys.linked_logins
  - 明文密码来源：DBPrivManagerApi.get_account_include_password
    入参 {bk_biz_id, users=去重 remote_user 列表, cluster_type=AccountType.SQLServer.value}
    出参 items 每项 {user, psw(base64)}；仓库不保存明文，实时向授权中心取
  - AES key 派生源：目标实例 IP（与 Go 端 Host 字段一致，见 CloneLinkserversParam.Host 注释）
  - 密文格式：base64( nonce(12B) || ciphertext(N B) || tag(16B) ) —— 参见 encrypt.py

与上下游模块的边界：
  - 上游：SQLServer 克隆配置子流程（common_sub_flow.clone_configs_sub_flow）
  - 下游：SqlserverActuatorScriptService._execute → Job 执行 sqlserver-actuator 克隆 linkserver
  - 若源实例无 linkserver：本组件直接返回成功，不下发 actuator
  - 若源实例仅有 use_self=True 的 linkserver：linkserver_secrets 为空列表，仍下发让目标端克隆
"""
import base64
import logging
from typing import Any, Dict, List, Optional, Tuple

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DBPrivManagerApi
from backend.db_services.dbpermission.constants import AccountType
from backend.flow.consts import SqlserverUserName
from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptService
from backend.flow.utils.sqlserver.encrypt import encrypt_login_password
from backend.flow.utils.sqlserver.payload_handler import PayloadHandler
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.flow.utils.sqlserver.sqlserver_db_function import get_source_linkservers

logger = logging.getLogger("flow")


class CloneLinkServerService(SqlserverActuatorScriptService):
    """SQLServer 实例之间克隆 LinkServer 的活动节点。

    职责：
      1. 通过 DRSApi 从源实例读取全部 linked-server 元数据
      2. 若源实例无任何 link-server，直接返回成功（提前结束，不再下发 actuator）
      3. 对 use_self=False 的记录，按 remote_user 去重后调用 DBPrivManagerApi 拉取明文密码，
         再用 encrypt_login_password 加密（key_seed = 目标实例 IP）
      4. 就地追加 linkserver_secrets 到 component_kwargs，交由父类完成 payload 下发

    kwargs 契约（在原 SqlserverActuatorScriptService 契约基础上）：
      - exec_ips: [{"ip": ..., "bk_cloud_id": ...}]，目标实例 host 列表，仅取首个
      - get_payload_func: 必须为 SqlserverActPayload.get_clone_linkserver_payload.__name__
      - component_kwargs: dict，本组件所需业务参数（由上游子流程注入），必须包含：
          * bk_biz_id: int，业务 ID，供 DBPrivManagerApi 授权中心按业务隔离查询密码
          * bk_cloud_id: int，云区域 ID，供 DRS RPC 直连源实例
          * source_host: str，源实例 IP（str，非 Host 对象）
          * source_port: int，源实例端口
          * target_port: int，目标实例端口
        本组件执行完毕后会就地追加 linkserver_secrets 字段到 component_kwargs，
        父类 SqlserverActuatorScriptService._execute 会将 component_kwargs 以 **
        展开传给 get_clone_linkserver_payload 作为显式命名参数消费

    边界 / 异常：
      - 源实例 RPC 失败：抛 Exception，交由 pipeline 引擎作失败重试
      - use_self=False 但 remote_user 为空：抛 Exception（不合法配置）
      - use_self=False 但 DBM 授权中心无对应 remote_user 的密码：抛 Exception（fail-fast）
      - 全部 linkserver 都是 use_self=True：linkserver_secrets 为空列表，仍下发 actuator 由目标端克隆
    """

    #: component_kwargs 必需字段清单；上游子流程必须全部注入，否则组件启动时 fail-fast
    #: 顺序按"来源实例 -> 目标实例 -> 业务上下文"分组，便于 review 时快速比对调用方
    _REQUIRED_COMPONENT_KWARGS: Tuple[str, ...] = (
        "bk_biz_id",
        "bk_cloud_id",
        "source_host",
        "source_port",
        "target_port",
    )

    def _execute(self, data, parent_data) -> bool:
        kwargs: Dict[str, Any] = data.get_one_of_inputs("kwargs")
        # 兜底空 dict，避免上游漏配 component_kwargs 直接抛 KeyError 造成栈信息不友好
        component_kwargs: Dict[str, Any] = kwargs.get("component_kwargs") or {}

        # 集中校验必需字段；异常里显式列出缺失名单，便于运维快速定位上游漏配
        missing_keys: List[str] = [k for k in self._REQUIRED_COMPONENT_KWARGS if k not in component_kwargs]
        if missing_keys:
            raise Exception(
                _("克隆 LinkServer 组件的 component_kwargs 缺少必需字段: {missing_keys}。请上游子流程注入这些字段，完整契约详见类文档。").format(
                    missing_keys=missing_keys
                )
            )

        # ---- 1) 解析业务参数（int() 均为防御性收敛，兼容上游误传 str/numpy int 等） ----
        source_host: str = component_kwargs["source_host"]
        if not source_host:
            raise Exception(_("component_kwargs['source_host'] 为空，请检查上游 Host 对象的构造过程。"))
        source_port: int = int(component_kwargs["source_port"])
        target_port: int = int(component_kwargs["target_port"])
        bk_cloud_id: int = int(component_kwargs["bk_cloud_id"])
        bk_biz_id: int = int(component_kwargs["bk_biz_id"])
        source_address: str = f"{source_host}:{source_port}"

        # ---- 2) 查询源实例的 link-server 元数据 ----
        link_server_rows: List[Dict[str, Any]] = get_source_linkservers(
            bk_cloud_id=bk_cloud_id, source_address=source_address
        )
        if not link_server_rows:
            # 源实例无 linkserver：直接提前结束，不下发 actuator，减少无意义的 Job 调用
            self.log_info(_("[{source_address}] 源实例不存在任何 linked-server，跳过克隆。").format(source_address=source_address))
            data.outputs.ext_result = True
            return True

        self.log_info(
            _("[{source_address}] 从源实例获取到 {count} 个 linked-server: {names}").format(
                source_address=source_address,
                count=len(link_server_rows),
                names=[row["name"] for row in link_server_rows],
            )
        )

        # ---- 3) 从 DBM 授权中心 / SA 密码服务拉取 use_self=False 的 remote_user 对应明文密码 ----
        remote_users: List[str] = self._collect_remote_users(link_server_rows=link_server_rows)
        password_map: Dict[str, str] = self._query_remote_user_passwords(
            bk_biz_id=bk_biz_id, remote_users=remote_users
        )

        # ---- 4) 目标 IP 作为 key_seed，加密并组装 secrets ----
        # 说明：exec_ips[0]['ip'] 与 payload.extend.host 是同一个 IP —— 父类
        # SqlserverActuatorScriptService._execute 会以 ips=exec_ips 传给 payload 方法，
        # payload 内部再取 kwargs['ips'][0]['ip'] 作为 extend.host。两侧 IP 严格一致，
        # 从而保证"AES key_seed"与"Go 端 CloneLinkserversParam.Host"完全对齐。
        target_host_ip: str = kwargs["exec_ips"][0]["ip"]
        link_server_secrets: List[Dict[str, str]] = self._build_linkserver_secrets(
            link_server_rows=link_server_rows,
            password_map=password_map,
            key_seed=target_host_ip,
        )

        # ---- 5) 通过 component_kwargs 向 payload 方法传递显式命名参数 ----
        # 与 get_data_export_payload 风格一致：payload 方法通过显式命名参数消费业务字段，
        # 父类 SqlserverActuatorScriptService._execute 会把 component_kwargs 以 ** 展开传入 payload 方法
        # 就地追加 linkserver_secrets，保留调用方传入的其他 component_kwargs 字段
        kwargs["get_payload_func"] = SqlserverActPayload.get_clone_linkserver_payload.__name__
        component_kwargs["linkserver_secrets"] = link_server_secrets

        self.log_info(
            _(
                "下发克隆 LinkServer 任务 -> 目标实例={target_host_ip}:{target_port}，待克隆凭据数量={count}（仅统计 use_self=false 的 linkserver）"
            ).format(
                target_host_ip=target_host_ip,
                target_port=target_port,
                count=len(link_server_secrets),
            )
        )
        return super()._execute(data, parent_data)

    @staticmethod
    def _collect_remote_users(link_server_rows: List[Dict[str, Any]]) -> List[str]:
        """从源端元数据中提取 use_self=False 记录的 remote_user 去重列表。

        设计要点 / 怎么做：
          - 只对 use_self=False 的行取 remote_user（use_self=True 无需下发密码）
          - 去重：多个 link-server 可能共用同一 remote_user，避免向授权中心重复查询
          - 空 remote_user 直接抛异常：SQL Server 语义上 use_self=False 必然对应显式登录名

        :param link_server_rows: 源实例查询结果（get_source_linkservers 输出）
        :return: 去重后的 remote_user 列表；若不存在 use_self=False 记录，返回空列表
        边界 / 异常：
          - use_self=False 但 remote_user 为空字符串：抛 Exception，携带对应 link-server 名单
        """
        remote_users: List[str] = []
        seen: set = set()
        invalid_names: List[str] = []

        for row in link_server_rows:
            if row["use_self"]:
                continue
            remote_user: str = row["remote_user"]
            if not remote_user:
                invalid_names.append(row["name"])
                continue
            if remote_user not in seen:
                seen.add(remote_user)
                remote_users.append(remote_user)

        if invalid_names:
            raise Exception(
                _("以下 linkserver 的 use_self=false 但 remote_user 为空: {invalid_names}。请检查源实例 linked_logins 的配置。").format(
                    invalid_names=invalid_names
                )
            )
        return remote_users

    @staticmethod
    def _query_remote_user_passwords(bk_biz_id: int, remote_users: List[str]) -> Dict[str, str]:
        """向 DBM 授权中心 / SA 密码服务查询指定 remote_user 列表对应的明文密码。

        设计要点 / 怎么做：
          - 分流：将 remote_users 按"是否 sa 账号"分为两类，两类的密码来源不同：
              * 普通业务账号 -> DBPrivManagerApi.get_account_include_password（授权中心）
              * SQL Server 内置 sa 账号 -> PayloadHandler.get_sa_account（密码服务专用通道）
            分流依据大小写不敏感比较（SQL Server 登录名不区分大小写，运维可能写成 SA/Sa/sa）
          - 授权中心 cluster_type = AccountType.SQLServer.value，按业务隔离
          - 授权中心出参 items 中 psw 为 base64 编码的明文密码，本方法解码后返回
          - sa 通道仅需调用一次（返回全局默认 sa 密码），命中的所有 sa 变体共享同一密码
          - 保留调用方原始 remote_user 大小写作为返回 map 的 key，便于下游按 name 精确回查

        :param bk_biz_id: 业务 ID，来自 kwargs['component_kwargs']['bk_biz_id']；仅授权中心查询需要
        :param remote_users: 待查询的远程登录名列表（已去重）；空列表则直接返回 {}
        :return: {remote_user: plain_pwd_utf8}
        边界 / 异常：
          - remote_users 为空：直接返回 {}，不发起任何 RPC
          - base64 解码失败：不吞异常，向上抛出（属于授权中心数据脏，不应静默）
          - sa 通道返回结果缺失 sa_pwd 字段：抛 Exception（密码服务未登记 sa，需运维介入）
          - 授权中心查询若某 remote_user 未登记：该 key 不会出现在返回值，
            由下游 _build_linkserver_secrets 做 fail-fast 汇总
        """
        if not remote_users:
            return {}

        # ---- 分流：sa 账号 vs 普通业务账号 ----
        sa_login_name: str = SqlserverUserName.SA.value  # "sa"
        sa_users: List[str] = [u for u in remote_users if u.lower() == sa_login_name]
        normal_users: List[str] = [u for u in remote_users if u.lower() != sa_login_name]

        password_map: Dict[str, str] = {}

        # ---- 普通业务账号：走 DBM 授权中心 ----
        if normal_users:
            params: Dict[str, Any] = {
                "bk_biz_id": bk_biz_id,
                "users": normal_users,
                "cluster_type": AccountType.SQLServer.value,
            }
            items: List[Dict[str, Any]] = DBPrivManagerApi.get_account_include_password(params).get("items", []) or []
            password_map.update({item["user"]: base64.b64decode(item["psw"]).decode("utf-8") for item in items})

        # ---- sa 账号：走 PayloadHandler.get_sa_account（走密码服务专用通道） ----
        if sa_users:
            sa_account: Dict[str, Any] = PayloadHandler.get_sa_account() or {}
            sa_pwd: Optional[str] = sa_account.get("sa_pwd")
            if not sa_pwd:
                raise Exception(_("从 PayloadHandler.get_sa_account() 获取 sa 密码失败：sa_pwd 为空。请确认 DBM 密码服务已登记 sa 账号。"))
            # 对每个 sa 变体（SA / Sa / sa）都以其原始字符串为 key 注入，便于下游按 remote_user 精确取值
            for u in sa_users:
                password_map[u] = sa_pwd

        return password_map

    @staticmethod
    def _build_linkserver_secrets(
        link_server_rows: List[Dict[str, Any]],
        password_map: Dict[str, str],
        key_seed: str,
    ) -> List[Dict[str, str]]:
        """将源端元数据转换为 Go 端 LinkserverSecret 结构列表。

        设计要点 / 怎么做：
          - use_self=True 的记录：透传型，Go 端使用当前登录上下文，无需下发密码 -> 跳过
          - use_self=False 的记录：按 remote_user 从 password_map 取明文；缺失则 fail-fast
          - 加密 key_seed = 目标实例 IP，与 Go 端 CloneLinkServersParam.Host 一致

        :param link_server_rows: 源实例查询结果（get_source_linkservers 输出）
        :param password_map: {remote_user: plain_pwd}，由 _query_remote_user_passwords 提供
        :param key_seed: AES key 派生种子（目标实例 IP）
        :return: [{"name": ..., "remote_user": ..., "encrypted_pwd": ...}, ...]
                 长度可能为 0（全部 use_self=True 的情况）
        边界 / 异常：
          - use_self=False 但 password_map 无对应 remote_user：抛 Exception，携带缺失名单
        """
        secrets: List[Dict[str, str]] = []
        missing_users: List[str] = []

        for row in link_server_rows:
            if row["use_self"]:
                # 透传型：不需要下发远程凭据
                continue

            remote_user: str = row["remote_user"]
            plain_pwd: Optional[str] = password_map.get(remote_user)
            if not plain_pwd:
                missing_users.append(remote_user)
                continue

            encrypted_pwd: str = encrypt_login_password(key_seed=key_seed, plain_pwd=plain_pwd)
            secrets.append(
                {
                    "name": row["name"],
                    "remote_user": remote_user,
                    "encrypted_pwd": encrypted_pwd,
                }
            )

        if missing_users:
            raise Exception(
                _(
                    "在 DBM 授权中心未找到以下 remote_user 的明文密码: {missing_users}。请先在 DBM 平台注册这些账号（cluster_type=sqlserver）后再执行本单据。"
                ).format(missing_users=missing_users)
            )

        return secrets


class CloneLinkServerComponent(Component):
    name = __name__
    code = "sqlserver_clone_link_server"
    bound_service = CloneLinkServerService
