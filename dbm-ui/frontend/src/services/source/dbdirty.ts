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

import DirtyMachinesModel from '@services/model/db-resource/dirtyMachines';
import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
import MachineEventModel from '@services/model/db-resource/machineEvent';
import type { ListBase } from '@services/types';

import http from '../http';

const path = '/apis/db_dirty';

/**
 * 污点池列表
 */
export function getDirtyMachines(params: { limit: number; offset: number }) {
  return http
    .get<ListBase<DirtyMachinesModel[]>>(`${path}/query_dirty_machines/`, params, {
      catchError: true,
    })
    .then((res) => ({
      ...res,
      results: res.results.map(
        (item) =>
          new DirtyMachinesModel(
            Object.assign(item, {
              permission: Object.assign(item.permission, res.permission),
            }),
          ),
      ),
    }));
}

/**
 * 机器事件列表
 */
export function getMachineEvents(params: {
  bk_biz_id?: number;
  create_at__gte?: string;
  create_at__lte?: string;
  domain?: string;
  events?: string;
  ips?: string;
  limit?: number;
  offset?: number;
  operator?: string;
}) {
  return http.get<ListBase<MachineEventModel[]>>(`${path}/list_machine_events/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new MachineEventModel(item)),
  }));
}

/**
 * 获取主机当前周期的事件
 */
export function getHostCurrentEvent(params: { bk_host_id: number }) {
  return http
    .get<MachineEventModel[]>(`${path}/get_host_current_events/`, params)
    .then((res) => res.map((item: MachineEventModel) => new MachineEventModel(item)));
}

/**
 * 将污点池主机转移至待回收模块
 */
export function transferDirtyMachines(params: { bk_host_ids: number[] }) {
  return http.post(`${path}/transfer_dirty_machines/`, params);
}

/**
 * 删除污点池记录
 */
export function deleteDirtyRecords(params: { bk_host_ids: number[] }) {
  return http.delete(`${path}/delete_dirty_records/`, params);
}

/**
 * 故障池、待回收池列表
 */
export function getMachinePool(params: {
  bk_biz_id?: number;
  ips?: string;
  limit?: number;
  offset?: number;
  /**
   * 不传则为所有主机
   */
  pool?: 'fault' | 'recycle';
}) {
  return http.get<ListBase<FaultOrRecycleMachineModel[]>>(`${path}/query_machine_pool/`, params).then((res) => ({
    ...res,
    results: res.results.map((item: FaultOrRecycleMachineModel) => new FaultOrRecycleMachineModel(item)),
  }));
}

/**
 * 将主机转移至待回收/故障池模块
 */
export function transferMachinePool(params: {
  bk_host_ids: number[];
  remark?: string;
  source: 'fault' | 'recycle';
  target: 'fault' | 'recycle' | 'recycled';
}) {
  return http.post(`${path}/transfer_hosts_to_pool/`, params);
}
