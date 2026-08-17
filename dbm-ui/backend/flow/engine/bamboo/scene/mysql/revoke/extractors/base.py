# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Revoke 候选主机 Extractor · 抽象基类。

模块职责：
  - 定义 :class:`HostExtractor` 基类，固化 ``ticket_data["infos"]`` 骨架：
    外层统一校验 ``infos`` / ``bk_biz_id`` → 逐条调 :meth:`_extract_one_info`；
    子类通常只实现 :meth:`_extract_one_info` + 覆盖类属性 ``_err_prefix``
  - ticket_data schema 不走 ``infos`` 的"部署类"单据（HA / Single / TenDBCluster 等 ``apply_infos``
    结构）可直接 override :meth:`extract` 推翻骨架，自行实现

命名历史：
  - 旧名 ``ApplyHostExtractor`` 源于"仅服务于部署类单据"的初始语境；现已覆盖主从迁移 /
    重建 slave / 添加 slave / Proxy 替换 / Proxy 扩容等运维类单据，``Apply`` 限定词
    已不准确，故重命名为 ``HostExtractor``（与 ``revoke/host_check.py`` 的词根一致）

契约：
  - 只提取"本单从资源池申请到的新机器"，不含老集群成员机
  - 机器角色由子类根据 ticket_data 字段名硬编码指定
  - 字段非法 / 缺失一律抛 :class:`NormalTenDBFlowException`，由上层 revoke_flow 顶层 try/except 兜底
"""
import logging
from typing import Any, Dict, List

from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import ResourceGroup

logger = logging.getLogger("flow")


class HostExtractor:
    """Revoke 候选主机 Extractor 基类 · 默认实现"infos 遍历"模板骨架。

    职责：
      - 输入 ticket_data，输出 ``List[ResourceGroup]``
      - 默认实现 :meth:`extract` 固化"读 ``infos`` → 校验 → 读 ``bk_biz_id`` →
        逐条调 :meth:`_extract_one_info`"骨架，覆盖主从迁移 / 重建 slave / 添加 slave /
        Proxy 替换 / Proxy 扩容 等走 ``infos`` 的单据
      - 不走 ``infos`` 的部署类单据（``apply_infos`` 结构）直接 override :meth:`extract`
        自行实现，无需走模板

    子类接入契约（走默认骨架时）：
      - 覆盖类属性 :attr:`_err_prefix`，形如 ``"[MysqlAddSlaveExtractor]"``；
        用于基类校验失败消息中快速定位来源
      - 实现 :meth:`_extract_one_info`，输入已校验为 dict 的 info + 索引 + bk_biz_id，
        **返回 ``List[ResourceGroup]``**（统一支持"一个 info 一组"与"一个 info 多组"两种语义：
        前者 ``return [group]``；后者 ``return [group_a, group_b, ...]``，由基类自动展平）；
        不实现则运行默认模板时抛 :class:`NotImplementedError`

    子类接入契约（override extract 时）：
      - 直接 override :meth:`extract`，可以不实现 :meth:`_extract_one_info`
        （基类默认 ``raise NotImplementedError``，只要 extract 不调用它就不触发）
      - 输出的每个 ``ResourceGroup`` 必须至少包含 1 个 unit
      - 每个 unit 的 role 必须使用与 host_check.py 契约一致的字符串
        （proxy / backend_master / backend_slave / spider / spider_slave / remote_master / remote_slave / single）

    设计选择：
      - 本类**不继承 abc.ABC**：有具体默认实现的类再挂 ABC 徒增认知负担；
        子类不实现 ``_extract_one_info`` 时的失败行为由"运行时 ``NotImplementedError``"兜底，
        与"ABC 实例化期 ``TypeError``"等效，且允许部署类子类无样板

    线程安全：是（无实例状态）
    """

    #: 日志/异常前缀：使用默认 extract 骨架的子类必须覆盖（如 ``"[MysqlAddSlaveExtractor]"``）
    _err_prefix: str = ""

    def extract(self, ticket_data: Dict) -> List[ResourceGroup]:
        """从 ``ticket_data["infos"]`` 提取候选组列表（默认模板）。

        设计要点 / 怎么做：
          - 外层统一校验 ``infos`` 是 list、``bk_biz_id`` 可整型化；
          - 对每条 info 先校验是 dict，再调子类 :meth:`_extract_one_info` 完成装配；
          - 子类不再重复写"infos 校验 / bk_biz_id 规整 / info 是 dict 校验"三段；
          - 若本单据 ticket_data 不走 ``infos``（如部署类 ``apply_infos``），子类直接 override 本方法。

        :param ticket_data: 原单据的 flow ticket_data；期望含 ``infos`` + ``bk_biz_id``
        :return: ``List[ResourceGroup]``；``infos`` 为空列表时返回 ``[]``
        边界：
          - ``infos`` 缺失 / 非 list → 抛 :class:`NormalTenDBFlowException`
          - ``bk_biz_id`` 缺失或不可整型化 → 抛 :class:`NormalTenDBFlowException`
          - 单条 info 非 dict → 抛 :class:`NormalTenDBFlowException`
          - 任何未处理异常 → 冒泡给上层 ``revoke_flow`` 顶层 try/except 兜底
        """
        infos = ticket_data.get("infos")
        if not isinstance(infos, list):
            raise NormalTenDBFlowException(
                message="{} ticket_data.infos missing or not list: {!r}".format(self._err_prefix, infos)
            )

        bk_biz_id_raw = ticket_data.get("bk_biz_id")
        try:
            bk_biz_id_i: int = int(bk_biz_id_raw)
        except (TypeError, ValueError) as err:
            raise NormalTenDBFlowException(
                message="{} ticket_data.bk_biz_id illegal: {!r} ({})".format(self._err_prefix, bk_biz_id_raw, err)
            )

        groups: List[ResourceGroup] = []
        for idx, info in enumerate(infos):
            if not isinstance(info, dict):
                raise NormalTenDBFlowException(
                    message="{} infos[{}] is not dict: {!r}".format(self._err_prefix, idx, info)
                )
            # extend：子类返回 List[ResourceGroup]，一条 info 可展开 1 组或 N 组（如 proxy 扩容"一台一组"）
            groups.extend(self._extract_one_info(info=info, info_idx=idx, bk_biz_id=bk_biz_id_i))
        return groups

    def _extract_one_info(
        self,
        info: Dict[str, Any],
        info_idx: int,
        bk_biz_id: int,
    ) -> List[ResourceGroup]:
        """处理一条已校验为 dict 的 info，产出一个或多个 :class:`ResourceGroup`。

        默认 :meth:`extract` 模板的调用点；走默认模板的子类**必须** override。
        若子类自己 override 了 :meth:`extract` 不再走默认模板，则本方法无需实现，
        由基类默认实现"抛 NotImplementedError"兜底（永远不会被触发）。

        返回语义：
          - "一个 info 一组"场景（如主从迁移 / Slave 重建 / Slave 添加）：``return [group]``
          - "一个 info N 组"场景（如 Proxy 扩容：N 台新 proxy 相互独立）：
            ``return [group_1, group_2, ...]``；基类 :meth:`extract` 自动 ``extend`` 展平

        :param info: 单条 info 字典（基类已保证非 None 且是 dict）
        :param info_idx: info 在 ``infos`` 中的索引（供错误消息与 ``group_id`` 构造）
        :param bk_biz_id: 已规整为 int 的业务 id
        :return: ``List[ResourceGroup]``；至少 1 组，每组至少 1 个 unit
        边界：
          - 子类读取自己关心的字段；任一非法 / 缺失 → 抛 :class:`NormalTenDBFlowException`
          - 异常不要就地吞；一律冒泡给基类 :meth:`extract` 的调用方
        """
        raise NotImplementedError(
            "{}._extract_one_info not implemented; subclass must override either "
            "extract() or _extract_one_info()".format(type(self).__name__)
        )
