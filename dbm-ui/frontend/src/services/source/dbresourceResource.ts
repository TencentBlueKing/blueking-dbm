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
import ImportHostModel from '@services/model/db-resource/import-host';
import OperationModel from '@services/model/db-resource/Operation';

import http from '../http';
import type {
  HostDetails,
  ListBase,
} from '../types';

const path = '/apis/dbresource/resource';

/**
 * 资源删除
 */
export const removeResource = function (params: { bk_host_ids: number[] }) {
  return http.post<{ bk_host_ids: number[] }>(`${path}/delete/`, params);
};

/**
 * 获取机型列表
 */
export const fetchDeviceClass = function () {
  return http.get<string[]>(`${path}/get_device_class/`);
};

/**
 * 获取磁盘类型
 */
export const fetchDiskTypes = function () {
  return http.get<string[]>(`${path}/get_disktypes/`);
};

/**
 * 获取挂载点
 */
export const fetchMountPoints = function () {
  return http.get<string[]>(`${path}/get_mountpoints/`);
};

/**
 * 根据逻辑城市查询园区
 */
export const fetchSubzones = function (params: { citys: string }) {
  return http.get<string[]>(`${path}/get_subzones/`, params);
};

/**
 * 资源池导入
 */
export const importResource = function (params: {
  for_bizs: number[],
  resource_types: string[],
  hosts: Array<{
    ip: string,
    host_id: number,
    bk_cloud_id: number
  }>
}) {
  return http.post(`${path}/import/`, params);
};

/**
 * 资源池列表
 */
export const fetchList = function (params: Record<string, any>) {
  return http.post<ListBase<DbResourceModel[]>>(`${path}/list/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new DbResourceModel(item)),
  }));
};

/**
 * 获取DBA业务下的主机信息
 */
export const fetchListDbaHost = function (params: {
  limit: number,
  offset: number,
  search_content: string
}) {
  return http.get<{
    total: number,
    data: ImportHostModel[]
  }>(`${path}/list_dba_hosts/`, {
    search_content: params.search_content,
    start: params.offset,
    page_size: params.limit,
  }).then(data => ({
    count: data.total,
    results: data.data,
  }));
};

/**
 * 查询DBA业务下的主机信息
 */
export const fetchHostListByHostId = function (params: { bk_host_ids: string }) {
  return http.get<HostDetails[]>(`${path}/query_dba_hosts/`, params);
};

/**
 * 查询资源导入任务
 */
export const fetchImportTask = function () {
  return http.get<{
    bk_biz_id: number,
    task_ids: string[]
  }>(`${path}/query_import_tasks/`);
};

/**
 * 查询资源操作记录
 */
export const fetchOperationList = function (params: {
  limit: number,
  offset: number,
  begin_time: string,
  end_time: string
}) {
  return http.get<ListBase<OperationModel[]>>(`${path}/query_operation_list/`, params).then(data => ({
    ...data,
    results: data.results.map(item => new OperationModel(item)),
  }));
};

/**
 * 获取资源导入相关链接
 */
export const fetchResourceImportUrls = function () {
  return http.get<{
    bk_cmdb_url: string,
    bk_nodeman_url: string,
    bk_scr_url: string
  }>(`${path}/resource_import_urls/`);
};

/**
 * 获取规格主机数量
 */
export const getSpecResourceCount = function (params: {
  bk_biz_id: number,
  resource_type?: string,
  bk_cloud_id: number,
  spec_ids: number[]
}) {
  return http.post<Record<number, number>>(`${path}/spec_resource_count/`, params);
};

/**
 * 更新资源
 */
export const updateResource = function (params: {
  bk_host_ids: number[],
  for_bizs: number[],
  resource_types: string[],
  set_empty_biz: boolean,
  set_empty_resource_type: boolean,
  storage_device: Record<string, {size: number, disk_type: string}>
}) {
  return http.post(`${path}/update/`, params);
};
