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
import logging
import re
from typing import Any, Dict, List, Tuple

from django.utils.translation import gettext_lazy as _
from packaging.version import InvalidVersion, Version

from backend import env
from backend.exceptions import ApiError

from ..base import BaseApi
from ..domains import BKNODEMAN_APIGW_DOMAIN, BKNODEMGR_APIGW_DOMAIN

logger = logging.getLogger("root")


class BKNodeManJobStatusError(ApiError):
    """查询节点管理任务状态失败，status_code 为 HTTP 状态码，非 HTTP 层面的失败时为 None"""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class _BaseBKNodeManApi(BaseApi):
    MODULE = _("节点管理")
    HTTP_STATUS_OK = 200

    class JobStatusType(object):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        PROCESSING_STATUS = [PENDING, RUNNING]

    def get_job_status(self, job_id) -> str:
        """查询任务状态，返回 JobStatusType 中的状态"""
        raise NotImplementedError

    def get_job_url(self, job_id) -> str:
        """获取任务详情页地址"""
        raise NotImplementedError

    @classmethod
    def _parse_raw_response(cls, raw_response) -> Dict:
        """解析 DataAPI._send 返回的原始响应，失败时抛出 BKNodeManJobStatusError"""
        if raw_response.status_code != cls.HTTP_STATUS_OK:
            raise BKNodeManJobStatusError(
                f"code: {raw_response.status_code}, message: {raw_response.text or raw_response.reason}",
                status_code=raw_response.status_code,
            )
        try:
            response = raw_response.json()
        except ValueError as err:
            raise BKNodeManJobStatusError(_("解析响应出错: {}，响应内容: {}").format(err, raw_response.text))
        if not response.get("result", response.get("code") == 0):
            raise BKNodeManJobStatusError(_("接口返回失败: {}").format(raw_response.text))
        return response.get("data") or {}


class _BKNodeManV2Api(_BaseBKNodeManApi):
    BASE = BKNODEMAN_APIGW_DOMAIN

    def __init__(self):
        is_esb = self.is_esb()
        self.operate_plugin = self.generate_data_api(method="POST", url="api/plugin/operate/", description=_("插件操作任务"))
        self.job_details = self.generate_data_api(
            method="GET" if is_esb else "POST",
            url="api/job/details/" if is_esb else "api/job/{job_id}/details/",
            description=_("查询任务详情"),
        )
        self.ipchooser_host_details = self.generate_data_api(
            method="POST", url="core/api/ipchooser_host/details/", description=_("查询agent状态")
        )

    def get_job_status(self, job_id) -> str:
        raw_response = self.job_details._send(params={"job_id": job_id}, headers={})
        return self._parse_raw_response(raw_response).get("status")

    def get_job_url(self, job_id) -> str:
        return f"{env.BK_NODEMAN_URL}/#/task-list/detail/{job_id}"


class _BKNodeManV3Api(_BaseBKNodeManApi):
    """
    节点管理 v3(bk-nodemgr) 接口，对外提供与 v2 相同的 operate_plugin / ipchooser_host_details 协议
    """

    BASE = BKNODEMGR_APIGW_DOMAIN
    # 插件安装包代次，目前接口仅支持 2
    PLUGIN_GENERATION = 2
    PAGE_LIMIT = 1000
    AGENT_RUNNING_STATUS = "running"
    WORKFLOW_STATUS_MAP = {
        "running": _BaseBKNodeManApi.JobStatusType.RUNNING,
        "success": _BaseBKNodeManApi.JobStatusType.SUCCESS,
        "failed": _BaseBKNodeManApi.JobStatusType.FAILED,
        "partial_failed": _BaseBKNodeManApi.JobStatusType.FAILED,
    }

    def __init__(self):
        self.release_plugin_list = self.generate_data_api(
            method="POST", url="api/v3/package/release/plugin/list", description=_("查询插件安装包列表")
        )
        self.plugin_install = self.generate_data_api(method="POST", url="api/v3/plugin/install", description=_("安装插件"))
        self.plugin_workflow_list = self.generate_data_api(
            method="POST", url="api/v3/plugin/workflow/list", description=_("查询插件任务流列表")
        )
        self.topo_host_list = self.generate_data_api(
            method="POST", url="api/v3/topo/host/list", description=_("查询主机列表")
        )

    def _get_plugin_version(self, plugin_name: str) -> str:
        data = self.release_plugin_list(
            {
                "generation": self.PLUGIN_GENERATION,
                "page": {"offset": 0, "limit": self.PAGE_LIMIT},
                "exact_include_conditions": {"name": [plugin_name], "enabled": [True]},
            }
        )
        releases = [item["release"] for item in data.get("items") or []]
        if not releases:
            raise ApiError(_("节点管理未找到插件 {} 的可用安装包").format(plugin_name))

        default_versions = {release["version"] for release in releases if release.get("as_default")}
        if default_versions:
            version = max(default_versions, key=_version_sort_key)
            if len(default_versions) > 1:
                logger.warning(
                    "plugin %s has multiple default versions %s, use the latest %s",
                    plugin_name,
                    sorted(default_versions),
                    version,
                )
            return version

        version = max({release["version"] for release in releases}, key=_version_sort_key)
        logger.warning("plugin %s has no default version, use the latest %s", plugin_name, version)
        return version

    def operate_plugin(self, params: Dict, **kwargs) -> Dict:
        if params.get("job_type") != "MAIN_INSTALL_PLUGIN":
            raise ApiError(_("节点管理v3暂不支持插件操作类型: {}").format(params.get("job_type")))

        plugin_name = params["plugin_params"]["name"]
        version = params["plugin_params"].get("version") or self._get_plugin_version(plugin_name)
        plugins = [
            {"bk_host_id": bk_host_id, "plugin_name": plugin_name, "version": version}
            for bk_host_id in params["bk_host_id"]
        ]
        data = self.plugin_install({"plugin": plugins}, **kwargs)
        return {"job_id": data["workflow_id"]}

    def ipchooser_host_details(self, params: Dict, **kwargs) -> List[Dict]:
        bk_host_ids = list({host["host_id"] for host in params.get("host_list", [])})
        host_details = []
        for index in range(0, len(bk_host_ids), self.PAGE_LIMIT):
            chunk = bk_host_ids[index : index + self.PAGE_LIMIT]
            data = self.topo_host_list(
                {"page": {"offset": 0, "limit": len(chunk)}, "exact_include_conditions": {"bk_host_id": chunk}},
                **kwargs,
            )
            host_details.extend(
                {
                    "host_id": item["bk_host_id"],
                    # agent在线状态，0为不在线，1为在线
                    "alive": int((item.get("state") or {}).get("node_status") == self.AGENT_RUNNING_STATUS),
                }
                for item in data.get("items") or []
            )
        return host_details

    def get_job_status(self, job_id) -> str:
        params = {"page": {"offset": 0, "limit": 1}, "exact_include_conditions": {"workflow_id": [job_id]}}
        raw_response = self.plugin_workflow_list._send(params=params, headers={})
        items = self._parse_raw_response(raw_response).get("items") or []
        # 任务流刚创建时可能还查询不到
        if not items:
            return self.JobStatusType.PENDING
        status = items[0]["status"]
        return self.WORKFLOW_STATUS_MAP.get(status, status)

    def get_job_url(self, job_id) -> str:
        return f"{env.BK_NODEMGR_URL}/#/node-manager/history/detail/{job_id}?active=plugin"


def _version_sort_key(version: str) -> Tuple[int, Any]:
    try:
        return 1, Version(version)
    except InvalidVersion:
        return 0, tuple(int(num) for num in re.findall(r"\d+", version))


def _create_nodeman_api() -> _BaseBKNodeManApi:
    if env.BKNODEMAN_API_VERSION == "v3":
        return _BKNodeManV3Api()
    return _BKNodeManV2Api()


BKNodeManApi = _create_nodeman_api()
