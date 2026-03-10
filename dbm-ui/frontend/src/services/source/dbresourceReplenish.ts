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

import type { CreateReplenish } from '@services/model/db-resource/Replenish';
import type ReplenishModel from '@services/model/db-resource/Replenish';

import http from '../http';
import type { ListBase } from '../types';

const path = '/apis/dbresource/replenish';

/**
 * 查询资源补货记录
 */
export function fetchReplenish(params: {
  creator?: string;
  db_type?: string;
  id?: number;
  limit?: number;
  offset?: number;
}) {
  return http.get<
    ListBase<
      {
        create_at: string;
        creator: string;
        details: Record<string, number>;
        id: number;
        status: string[];
        ticket_ids: number[];
      }[]
    >
  >(`${path}/`, params);
}

/**
 * 海磊资源池主机补货
 */
export function createResourceReplenish(params: { bk_biz_id: number; infos: CreateReplenish[]; remark?: string }) {
  return http.post(`${path}/create_resource_replenish/`, params);
}

/**
 * 获取资源池单据申请交付信息
 */
export function listTicketApplyInfo(params: { limit?: number; offset?: number; ticket_ids: string }) {
  return http.get<
    Record<
      number,
      {
        apply_count: number;
        delivery_count: number;
        details: ReplenishModel;
      }
    >
  >(`${path}/list_ticket_apply_info/`, params);
}

/**
 * 查询正在运行的补货记录
 */
export function getRunningReplenishRecord() {
  return http.get<number>(`${path}/get_running_replenish_record/`);
}

/**
 * 导出补货单据Excel
 */
export function exportReplenishTickets(params: { replenish_record_ids: number[] }) {
  return http.post<string>(`${path}/export_replenish_tickets/`, params, { responseType: 'blob' });
}
