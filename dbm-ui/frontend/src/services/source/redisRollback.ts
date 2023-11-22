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
import RedisRollbackModel from '@services/model/redis/redis-rollback';

import { useGlobalBizs } from '@stores';

import http from '../http';
import type { ListBase } from '../types';

const { currentBizId } = useGlobalBizs();

const path = `/apis/redis/bizs/${currentBizId}/rollback`;

export const getRollbackList = function (params?: {
  bk_biz_id: number,
  limit?: number;
  offset?: number;
  temp_cluster_proxy?: string; // ip:port
} & Record<string, any>) {
  return http.get<ListBase<RedisRollbackModel[]>>(`${path}/`, params).then(res => ({
    ...res,
    results: res.results.map(item => new RedisRollbackModel(item)),
  }));
};
