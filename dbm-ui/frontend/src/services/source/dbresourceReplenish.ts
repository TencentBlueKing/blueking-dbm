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

import http from '../http';
import type { CreateReplenish } from '@services/model/db-resource/Replenish';
import type { ListBase } from '../types';
import type ReplenishModel from '@services/model/db-resource/Replenish';

const path = '/apis/dbresource/replenish';

/**
 * 查询资源补货记录
 */
export function fetchReplenish(params: {
  id?: number;
  db_type?: string;
  creator?: string;
  limit?: number;
  offset?: number;
}) {
  return http.get<
    ListBase<
      {
        id: number;
        status: string[];
        creator: string;
        create_at: string;
        details: Record<string, number>;
        ticket_ids: number[];
      }[]
    >
  >(`${path}/`, params);
}

/**
 * 海磊资源池主机补货
 */
export function createResourceReplenish(params: { infos: CreateReplenish[]; bk_biz_id: number; remark?: string }) {
  return http.post(`${path}/create_resource_replenish/`, params);
}

/**
 * 获取资源池单据申请交付信息
 */
export function listTicketApplyInfo(params: { ticket_ids: string; offset?: number; limit?: number }) {
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
