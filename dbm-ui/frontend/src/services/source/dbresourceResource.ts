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

import { DBTypes, MachineEvents } from '@common/const';

import http, { type IRequestPayload } from '../http';

const path = '/apis/dbresource/resource';

/**
 * 资源删除
 */
export function removeResource(params: {
  event: 'to_recycle' | 'to_fault' | 'undo_import';
  hosts: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }[];
  remark?: string;
}) {
  return http.post<{ bk_host_ids: number[] }>(`${path}/delete/`, params);
}

/**
 * 获取机型列表（带 CPU / 内存 / 磁盘规格）
 */
export function fetchDeviceClass(params: { device_type?: string; limit?: number; offset?: number }) {
  return http.get<
    ListBase<
      {
        cpu: number;
        device_type: string;
        disk: number;
        id: number;
        mem: number;
      }[]
    >
  >(`${path}/get_device_class/`, params);
}

/**
 * 获取资源池主机机型列表
 */
export function fetchResourceHostDeviceClass() {
  return http.get<string[]>(`${path}/get_resource_host_device_class/`);
}

/**
 *
 * @deprecated 获取磁盘类型（存量）。固定的枚举值，直接查询全量的数据就好
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
  bk_biz_id: number;
  for_biz: number;
  hosts: Array<{
    bk_cloud_id: number;
    host_id: number;
    ip: string;
  }>;
  label_names: string[];
  labels: number[];
  resource_type: string;
  return_resource?: boolean; // 是否 故障池，待回收池 转入资源池
}) {
  return http.post<{
    ticket_ids: number[];
  }>(`${path}/import/`, params, {
    catchError: true,
  });
}

interface ResouceListParams {
  agent_status?: string;
  bk_cloud_ids?: string;
  city?: string;
  cpu?: string;
  device_class?: string;
  disk?: string;
  disk_type?: string;
  for_biz?: number;
  headers?: { id: string; name?: string }[];
  hosts?: string;
  label_names?: string;
  limit?: number;
  mem?: string;
  mount_point?: string;
  offset?: number;
  os_names?: string;
  os_type?: string;
  resource_type?: string;
  spec_id?: string;
  subzone_ids?: string;
}

/**
 * 资源池列表
 */
export function fetchList(params: ResouceListParams, payload = {} as IRequestPayload) {
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
 * 资源池导出
 */
export function resourceExport(params: ResouceListParams) {
  return http.post<string>(`${path}/resource_export/`, params, { responseType: 'blob' });
}

/**
 * 获取DBA业务下的主机信息
 */
export function fetchListDbaHost(params: {
  bk_biz_id: number;
  bk_idc_city_name: string;
  bk_sub_zone: string;
  bk_svr_device_class_name: string;
  limit: number;
  offset: number;
  operator: string;
  os_name: string;
  search_content: string;
}) {
  return http
    .get<{
      data: HostInfo[];
      total: number;
    }>(`${path}/list_dba_hosts/`, {
      ...params,
      bk_biz_id: params.bk_biz_id,
      page_size: params.limit,
      start: params.offset,
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
// export function fetchImportTask() {
//   return http.get<{
//     bk_biz_id: number;
//     task_ids: string[];
//   }>(`${path}/query_import_tasks/`);
// }

/**
 * 查询资源操作记录
 */
export function fetchOperationList(
  params: {
    begin_time: string;
    end_time: string;
    limit: number;
    offset: number;
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
  bk_cloud_id: number;
  city?: string;
  resource_type?: string;
  spec_ids: number[];
  sub_zone_ids?: string[];
}) {
  return http.post<Record<number, number>>(`${path}/spec_resource_count/`, params);
}

/**
 * 更新资源
 */
export function updateResource(params: {
  bk_biz_id?: number; // update_type 相关字段，当前业务id
  bk_host_ids: number[];
  city_meta?: {
    city: string;
    city_id: string;
  };
  device_class?: string;
  for_biz?: number;
  host_id_ip_map?: Record<string, string>; // update_type 相关字段
  labels?: number[];
  rack_id?: string;
  remark?: {
    [key: string]: {
      after_value: string;
      before_value: string;
    };
  }[]; // update_type 相关字段
  resource_type?: string;
  storage_device?: Record<string, { disk_type: string; size: number }>;
  sub_zone_meta?: {
    sub_zone: string;
    sub_zone_id: string;
  };
  update_type?: MachineEvents.HOST_ATTRIBUTE | MachineEvents.RESOURCE_OWNER; // 修改资源归属或修改主机属性
}) {
  return http.post(`${path}/update/`, params);
}

/**
 * 获取操作系统类型
 */
export function getOsTypeList(params: { limit?: number; offset?: number }) {
  return http.get<string[]>(`${path}/get_os_types/`, params);
}

/**
 * 获取操作系统名称
 */
export function getResourceOsName() {
  return http.post<{
    os_names: {
      text: string;
      value: string;
    }[];
  }>(`${path}/resource_osname/`);
}

/**
 * 按照组件统计资源数量
 */
export function getGroupCount() {
  return http.post<{ count: number; rs_type: string }[]>(`${path}/resource_group_count/`);
}

/**
 * 按照条件聚合资源统计
 */
export function getSummaryList(params: {
  city?: string;
  cluster_type?: string;
  db_type: DBTypes;
  enable_spec?: boolean;
  for_biz?: number;
  group_by: string;
  machine_type?: string;
  spec_id_list?: number[];
  sub_zones?: string[];
}) {
  return http
    .get<{
      no_spec_ip_list: string[];
      summary_data: SummaryModel[];
    }>(`${path}/resource_summary/`, params)
    .then((data) => ({
      count: data.summary_data.length || 0,
      results: {
        no_spec_ip_list: data.no_spec_ip_list || [],
        summary_data: data.summary_data.map((item) => new SummaryModel(item)),
      },
    }));
}

/**
 * 追加主机标签
 */
export function appendHostLabel(params: {
  bk_biz_id: number;
  bk_host_ids: number[];
  host_id_ip_map: Record<string, string>;
  labels: number[];
  remark: {
    [key: string]: {
      after_value: string;
      before_value: string;
    };
  }[];
}) {
  return http.post(`${path}/append_labels/`, params);
}

// 计算预估成本
export function specCostEstimate(params: {
  db_type: string;
  resource_spec: {
    [key: string]: {
      count: number;
      spec_id: number;
    };
  };
}) {
  return http.post<number>(`${path}/spec_cost_estimate/`, params);
}

/**
 * 计算资源池水位信息
 */
export function calcResourceWaterLevel(params: { cache: boolean }) {
  return http.post<{
    exclusive_machine: {
      empty_city: string[];
      empty_os: string[];
      empty_subzone: string[];
    };
    exclusive_spec: {
      spec_id: number;
      spec_name: string;
    }[];
    flush_time: string;
    update_time: string;
    water_level: {
      city: string;
      db_type: string;
      machine_count: number;
      machine_refer_count: number;
      os_name: string;
      resource_count: number;
      spec_id: number;
      spec_machine_type: string;
      spec_name: string;
      subzone: string;
    }[];
  }>(`${path}/calc_resource_water_level/`, params);
}

/**
 * 获取同母机 IP 列表
 */
export function fetchSameSvrOwnerIps(params: { bk_host_id: number }) {
  return http.post<{
    bk_host_id: number;
    bk_svr_owner_asset_id: string;
    count: number;
    ips: string[];
  }>(`${path}/same_svr_owner_ips/`, params);
}
