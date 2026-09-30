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

from typing import Dict

# 部署模式相关的请求参数名(共享集群/独占集群)
DEPLOY_PARAM_KEYS = ["isPublic", "bkBizId"]


def parse_deploy_params(req_params: dict, bk_biz_id: int = None) -> Dict:
    """解析部署模式参数，用于透传给k8s接口

    @param req_params: 请求参数(可为查询参数或已校验的序列化数据)
    @param bk_biz_id: 业务ID，未显式传入 bkBizId 时取此值
    @return: {"isPublic": bool, "bkBizId": int(可选)}
        isPublic: 是否共享集群(True-共享集群/公共集群，False-独占集群)，缺省为共享集群
        bkBizId: 独占集群所属的业务ID
    """
    is_public = req_params.get("isPublic", True)
    # 查询参数均为字符串，需兼容 "true"/"false"
    if isinstance(is_public, str):
        is_public = is_public.lower() != "false"

    deploy_params = {"isPublic": is_public}
    bk_biz_id = req_params.get("bkBizId") or bk_biz_id
    if bk_biz_id:
        deploy_params["bkBizId"] = int(bk_biz_id)
    return deploy_params


def get_deploy_params_from_request(request, bk_biz_id: int = None) -> Dict:
    """从请求中解析部署模式参数：GET取query_params，POST允许放在请求体中"""
    req_params = request.query_params.dict()
    if isinstance(request.data, dict):
        req_params.update({key: request.data[key] for key in DEPLOY_PARAM_KEYS if key in request.data})
    return parse_deploy_params(req_params, bk_biz_id)


def offset_to_page(params: dict) -> dict:
    """将 offset/limit 转换为 page/limit 并返回新 dict"""
    offset = params.pop("offset", 0)
    params["page"] = offset // params["limit"] + 1
    return params
