/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import DeployPlanModel from '@services/model/db-resource/DeployPlan';

import http from '../http';
import type { ListBase } from '../types';

const path = '/apis/dbresource/deploy_plan';

/**
 * 查询部署方案列表
 */
export function fetchDeployPlan(params: { cluster_type: string; limit: number; offset: number; name?: string }) {
  return http.get<ListBase<DeployPlanModel[]>>(`${path}/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new DeployPlanModel(item)),
  }));
}

/**
 * 新建部署方案
 */
export function createDeployPlan(params: Record<string, any>) {
  return http.post(`${path}/`, params);
}

/**
 * 批量删除部署方案
 */
export function batchRemoveDeployPlan(params: { deploy_plan_ids: number[] }) {
  return http.delete(`${path}/batch_delete/`, params);
}

/**
 * 更新部署方案
 */
export function updateDeployPlan(params: { id: number }) {
  return http.delete(`${path}/${params.id}/`);
}

/**
 * 删除部署方案
 */
export function removeDeployPlan(params: { id: number }) {
  return http.delete(`${path}/${params.id}/`);
}
