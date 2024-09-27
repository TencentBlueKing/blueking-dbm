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
import OperationModel from '@services/model/db-resource/Operation';
import SummaryModel from '@services/model/db-resource/summary';
import type { HostInfo, ListBase } from '@services/types';

import type { DBTypes } from '@common/const';

import http, { type IRequestPayload } from '../http';

const path = '/apis/dbresource/resource';

/**
 * 资源删除
 */
export function removeResource(params: { bk_host_ids: number[] }) {
  return http.post<{ bk_host_ids: number[] }>(`${path}/delete/`, params);
}

/**
 * 获取机型列表
 */
export function fetchDeviceClass() {
  return http.get<string[]>(`${path}/get_device_class/`);
}

/**
 * 获取磁盘类型
 */
export function fetchDiskTypes() {
  return http.get<string[]>(`${path}/get_disktypes/`);
}

/**
 * 获取挂载点
 */
export function fetchMountPoints() {
  return http.get<string[]>(`${path}/get_mountpoints/`);
}

/**
 * 资源池导入
 */
export function importResource(params: {
  for_biz: number;
  resource_type: string;
  hosts: Array<{
    ip: string;
    host_id: number;
    bk_cloud_id: number;
  }>;
}) {
  return http.post(`${path}/import/`, params);
}

/**
 * 资源池列表
 */
export function fetchList(params: Record<string, any>, payload = {} as IRequestPayload) {
  return http.post<ListBase<DbResourceModel[]>>(`${path}/list/`, params, payload).then((data) => ({
    ...data,
    results: data.results.map(
      (item) =>
        new DbResourceModel(
          Object.assign(item, {
            permission: data.permission,
          }),
        ),
    ),
  }));
}

/**
 * 获取DBA业务下的主机信息
 */
export function fetchListDbaHost(params: { limit: number; offset: number; search_content: string }) {
  return http
    .get<{
      total: number;
      data: HostInfo[];
    }>(`${path}/list_dba_hosts/`, {
      search_content: params.search_content,
      start: params.offset,
      page_size: params.limit,
    })
    .then((data) => ({
      count: data.total,
      results: data.data,
    }));
}

/**
 * 查询DBA业务下的主机信息
 */
export function fetchHostListByHostId(params: { bk_host_ids: string }) {
  return http.get<HostInfo[]>(`${path}/query_dba_hosts/`, params);
}

/**
 * 查询资源导入任务
 */
export function fetchImportTask() {
  return http.get<{
    bk_biz_id: number;
    task_ids: string[];
  }>(`${path}/query_import_tasks/`);
}

/**
 * 查询资源操作记录
 */
export function fetchOperationList(
  params: {
    limit: number;
    offset: number;
    begin_time: string;
    end_time: string;
  },
  payload = {} as IRequestPayload,
) {
  return http.get<ListBase<OperationModel[]>>(`${path}/query_operation_list/`, params, payload).then((data) => ({
    ...data,
    results: data.results.map((item) => new OperationModel(item)),
  }));
}

/**
 * 获取资源导入相关链接
 */
export function fetchResourceImportUrls() {
  return http.get<{
    bk_cmdb_url: string;
    bk_nodeman_url: string;
    bk_scr_url: string;
  }>(`${path}/resource_import_urls/`);
}

/**
 * 获取规格主机数量
 */
export function getSpecResourceCount(params: {
  bk_biz_id: number;
  city?: string;
  resource_type?: string;
  bk_cloud_id: number;
  spec_ids: number[];
}) {
  return http.post<Record<number, number>>(`${path}/spec_resource_count/`, params);
}

/**
 * 更新资源
 */
export function updateResource(params: {
  bk_host_ids: number[];
  for_biz: number;
  rack_id: string;
  resource_type: string;
  set_empty_biz: boolean;
  set_empty_resource_type: boolean;
  storage_device: Record<string, { size: number; disk_type: string }>;
}) {
  return http.post(`${path}/update/`, params);
}

/**
 * 获取操作系统类型
 */
export function getOsTypeList(params: { offset?: number; limit?: number }) {
  return http.get<string[]>(`${path}/get_os_types/`, params);
}

/**
 * 按照组件统计资源数量
 */
export function getGroupCount() {
  return http.post<{ rs_type: string; count: number }[]>(`${path}/resource_group_count/`);
}

/**
 * 按照条件聚合资源统计
 */
export function getSummaryList(params: {
  group_by: string;
  for_biz?: number;
  city?: string;
  sub_zones?: string[];
  spec_param: {
    db_type: DBTypes;
    machine_type?: string;
    cluster_type?: string;
    spec_id_list?: number[];
  };
}) {
  return http.get<SummaryModel[]>(`${path}/resource_summary/`, params).then((data) => ({
    count: data.length || 0,
    results: data.map((item) => new SummaryModel(item)),
  }));
}
