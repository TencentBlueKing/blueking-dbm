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

import DbResourceModel from '@services/model/db-resource/DbResource';
import DeployPlanModel from '@services/model/db-resource/DeployPlan';
import OperationModel from '@services/model/db-resource/Operation';
import ResourceSpecModel from '@services/model/resource-spec/resourceSpec';

import http from './http';
import type {
  HostDetails,
} from './types/ip';

// 查询部署方案列表
export function fetchDeployPlan(params: {
  cluster_type: string,
  limit: number,
  offset: number,
  name?: string
}) {
  return http.get<{ count: number, results: DeployPlanModel[] }>('/apis/dbresource/deploy_plan/', params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new DeployPlanModel(item)),
    }));
}

// 新建部署方案
export function createDeployPlan(params: Record<string, any>) {
  return http.post('/apis/dbresource/deploy_plan/', params);
}

// 批量删除部署方案
export function batchRemoveDeployPlan(params: { deploy_plan_ids: number[] }) {
  return http.delete('/apis/dbresource/deploy_plan/batch_delete/', params);
}
// 更新部署方案
export function updateDeployPlan(params: { id: number }) {
  return http.delete(`/apis/dbresource/deploy_plan/${params.id}/`);
}
// 删除部署方案
export function removeDeployPlan(params: { id: number }) {
  return http.delete(`/apis/dbresource/deploy_plan/${params.id}/`);
}
// 资源池列表
export function fetchList(params: Record<string, any>) {
  return http.post<{ count: number, results: DbResourceModel[] }>('/apis/dbresource/resource/list/', params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new DbResourceModel(item)),
    }));
}

// 资源池导入
export function importResource(params: {
  for_bizs: number[],
  resource_types: string[],
  hosts: Array<{ ip: string, host_id: number, bk_cloud_id: number }>
}) {
  return http.post('/apis/dbresource/resource/import/', params);
}

// 获取磁盘类型
export function fetchDiskTypes() {
  return http.get<{code: number, request_id: string}[]>('/apis/dbresource/resource/get_disktypes/');
}

// 获取挂载点
export function fetchMountPoints() {
  return http.get<string[]>('/apis/dbresource/resource/get_mountpoints/');
}

// 根据逻辑城市查询园区
export function fetchSubzones(params: {citys: string}) {
  return http.get<string[]>('/apis/dbresource/resource/get_subzones/', params);
}

// 获取机型列表
export function fetchDeviceClass() {
  return http.get<{code: number, request_id: string}[]>('/apis/dbresource/resource/get_device_class/');
}

// 获取DBA业务下的主机信息
export function fetchListDbaHost(params: { limit: number, offset: number, search_content: string }) {
  return http.get<{ total: number, data: HostDetails[] }>('/apis/dbresource/resource/list_dba_hosts/', {
    search_content: params.search_content,
    start: params.offset,
    page_size: params.limit,
  })
    .then(data => ({
      count: data.total,
      results: data.data,
    }));
}

// 资源删除
export function removeResource(params: { bk_host_ids: number[] }) {
  return http.post<{ bk_host_ids: number[] }>('/apis/dbresource/resource/delete/', params);
}

// 查询资源导入任务
export function fetchImportTask() {
  return http.get<{bk_biz_id: number, task_ids: string[]}>('/apis/dbresource/resource/query_import_tasks/');
}

// 获取资源导入相关链接
export function fetchResourceImportUrls() {
  return http.get<{
    bk_cmdb_url: string,
    bk_nodeman_url: string,
    bk_scr_url: string
  }>('/apis/dbresource/resource/resource_import_urls/');
}

// 查询资源操作记录
export function fetchOperationList(params: {
  limit: number,
  offset: number,
  begin_time: string,
  end_time: string
}) {
  return http.get<{ count: number, results: OperationModel[] }>('/apis/dbresource/resource/query_operation_list/', params)
    .then(data => ({
      ...data,
      results: data.results.map(item => new OperationModel(item)),
    }));
}

// 查询DBA业务下的主机信息
export function fetchHostListByHostId(params: { bk_host_ids: string }) {
  return http.get<HostDetails[]>('/apis/dbresource/resource/query_dba_hosts/', params);
}

// 更新资源
export function updateResource(params: {
  bk_host_ids: number[],
  for_bizs: number[],
  resource_types: string[]
}) {
  return http.post('/apis/dbresource/resource/update/', params);
}

// 获取推荐规格
export function fetchRecommendSpec(params: {
  cluster_id: number,
  role: string,
}| {
  instance_id: number,
  role: string,
}) {
  return http.get<ResourceSpecModel[]>('/apis/dbresource/spec/recommend_spec/', params)
    .then(data => data.map(item => new ResourceSpecModel(item)));
}
