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
import type { ListBase } from '../types';

const path = '/apis/conf/ip_whitelist';

/**
 * IP白名单列表项
 */
interface WhitelistItem {
  ips: string[],
  is_global: boolean,
  remark: string
  bk_biz_id: number
  create_at: string,
  creator: string,
  id: number,
  update_at: string,
  updater: string
}

/**
 * IP白名单列表
 */
export function getWhitelist(params: Record<string, any> & { bk_biz_id: number }) {
  return http.post<ListBase<WhitelistItem[]>>(`${path}/iplist/`, params);
}

/**
 * 编辑、新建参数
 */
interface WhitelistOperationData {
  id: number
  bk_biz_id: number,
  ips: string[],
  remark: string,
}

/**
 * 新建IP白名单
 */
export function createWhitelist(params: Omit<WhitelistOperationData, 'id'>) {
  return http.post(`${path}/`, params);
}

/**
 * 编辑IP白名单
 */
export function updateWhitelist(params: WhitelistOperationData) {
  return http.put(`${path}/${params.id}/`, params);
}

/**
 * 删除IP白名单
 */
export function batchDeleteWhitelist(params: { ids: number[] }) {
  return http.delete(`${path}/batch_delete/`, params);
}
