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

from backend import env

from .backends import BaseItsmBackend


class _ItsmApiAdapter:
    """根据版本路由到对应的 ITSM 后端实现。"""

    V3 = "v3"
    V4 = "v4"

    def __init__(self):
        self._backend_instances = {}

    @property
    def api_version(self):
        """获取当前配置的 ITSM API 版本。"""
        return str(env.ITSM_API_VERSION).lower()

    def _get_itsm_version_by_sn(self, sn):
        """根据单据 sn 判断历史单据所属的 ITSM 后端版本。"""
        if isinstance(sn, (list, tuple)):
            sn = sn[0] if sn else ""
        sn = str(sn)

        for itsm_version, backend_cls in BaseItsmBackend.backends.items():
            sn_prefix = getattr(backend_cls, "SN_PREFIX", "")
            if sn_prefix and sn.startswith(sn_prefix):
                return itsm_version
        return self.V3

    def _backend(self, params=None, itsm_version=None):
        """根据单据 sn 或指定版本获取对应的 ITSM 后端实例。"""
        if itsm_version is None and params is not None:
            itsm_version = self._get_itsm_version_by_sn(params.get("sn"))
        itsm_version = (itsm_version or self.api_version or self.V3).lower()
        backend_cls = BaseItsmBackend.backends.get(itsm_version) or BaseItsmBackend.backends[self.V3]
        if itsm_version not in self._backend_instances:
            self._backend_instances[itsm_version] = backend_cls()
        return self._backend_instances[itsm_version]

    def create_ticket(self, params, *args, **kwargs):
        """创建 ITSM 单据。"""
        return self._backend().create_ticket(params, *args, **kwargs)

    def ticket_approval_result(self, params, *args, **kwargs):
        """查询 ITSM 单据审批结果。"""
        return self._backend(params).ticket_approval_result(params, *args, **kwargs)

    def get_ticket_logs(self, params, *args, **kwargs):
        """查询 ITSM 单据日志。"""
        return self._backend(params).get_ticket_logs(params, *args, **kwargs)

    def get_ticket_info(self, params, *args, **kwargs):
        """查询 ITSM 单据详情。"""
        return self._backend(params).get_ticket_info(params, *args, **kwargs)

    def operate_node(self, params, *args, **kwargs):
        """处理 ITSM 单据节点。"""
        return self._backend(params).operate_node(params, *args, **kwargs)

    def operate_ticket(self, params, *args, **kwargs):
        """处理 ITSM 单据。"""
        return self._backend(params).operate_ticket(params, *args, **kwargs)

    def migrate_system(self, params, *args, **kwargs):
        """迁移 ITSM V4 系统流程。"""
        return self._backend(itsm_version=self.V4).migrate_system(params, *args, **kwargs)

    def get_ticket_status(self, params, *args, **kwargs):
        """查询 ITSM 单据状态。"""
        return self._backend(itsm_version=self.V3).get_ticket_status(params, *args, **kwargs)

    def get_service_catalogs(self, params, *args, **kwargs):
        """查询 ITSM 服务目录。"""
        return self._backend(itsm_version=self.V3).get_service_catalogs(params, *args, **kwargs)

    def get_services(self, params, *args, **kwargs):
        """查询 ITSM 服务列表。"""
        return self._backend(itsm_version=self.V3).get_services(params, *args, **kwargs)

    def create_service_catalog(self, params, *args, **kwargs):
        """创建 ITSM 服务目录。"""
        return self._backend(itsm_version=self.V3).create_service_catalog(params, *args, **kwargs)

    def import_service(self, params, *args, **kwargs):
        """导入 ITSM 服务。"""
        return self._backend(itsm_version=self.V3).import_service(params, *args, **kwargs)

    def update_service(self, params, *args, **kwargs):
        """更新 ITSM 服务。"""
        return self._backend(itsm_version=self.V3).update_service(params, *args, **kwargs)


ItsmApiAdapter = _ItsmApiAdapter()
