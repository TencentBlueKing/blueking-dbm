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
import type { ListBase } from '../types/common';
import type { WhitelistOperationData } from '../types/whitelist';

// IP 白名单列表
export const getWhitelist = function (params: Record<string, any> & { bk_biz_id: number })
: Promise<ListBase<any[]>> {
  return http.post('/apis/conf/ip_whitelist/iplist/', params);
};

// 创建白名单
export const createWhitelist = function (params: WhitelistOperationData) {
  return http.post('/apis/conf/ip_whitelist/', params);
};

// 编辑白名单
export const updateWhitelist = function (params: WhitelistOperationData & { id: number }) {
  return http.put(`/apis/conf/ip_whitelist/${params.id}/`, params);
};

// 删除白名单
export const batchDeleteWhitelist = function (params: { ids: number[] }) {
  return http.delete('/apis/conf/ip_whitelist/batch_delete/', params);
};
