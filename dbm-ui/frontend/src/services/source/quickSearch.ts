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

import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
import QuickSearchClusterModel from '@services/model/quiker-search/quick-search-cluster';
import QuickSearchInstanceModel from '@services/model/quiker-search/quick-search-instance';
import TaskFlowModel from '@services/model/taskflow/taskflow';
import TicketModel from '@services/model/ticket/ticket';

import http from '../http';

/**
 * 全局搜索
 *
 * keyword 和 short_code 二选一, 不能同时为空
 */
export function quickSearch(params: {
  bk_biz_ids: number[];
  db_types: string[];
  filter_type: string;
  keyword?: string;
  limit?: number;
  resource_types: string[];
  short_code?: string;
}) {
  return http
    .post<{
      cluster: QuickSearchClusterModel[];
      count: {
        cluster: number;
        instance: number;
        machine: number;
        task: number;
        ticket: number;
      };
      instance: QuickSearchInstanceModel[];
      keyword: string;
      machine: FaultOrRecycleMachineModel[];
      short_code: string;
      task: TaskFlowModel[];
      ticket: TicketModel<unknown>[];
    }>('/apis/quick_search/search/', params)
    .then((res) => ({
      ...res,
      cluster: (res.cluster || []).map((item) => new QuickSearchClusterModel(item)),
      count: {
        cluster: res.count.cluster || 0,
        instance: res.count.instance || 0,
        machine: res.count.machine || 0,
        task: res.count.task || 0,
        ticket: res.count.ticket || 0,
      },
      instance: (res.instance || []).map((item) => new QuickSearchInstanceModel(item)),
      machine: (res.machine || []).map((item) => new FaultOrRecycleMachineModel(item)),
      task: (res.task || []).map((item) => new TaskFlowModel(item)),
      ticket: (res.ticket || []).map((item) => new TicketModel(item)),
    }));
}

/**
 * 全局搜索结果页具体数据
 *
 */
export function quickSearchResult(params: {
  bk_biz_ids: number[];
  db_types: string[];
  filter_type: string;
  keyword?: string;
  limit?: number;
  offset?: number;
  resource_type: string;
  resource_types: string[];
}) {
  return http
    .post<{
      count: number;
      page: number;
      page_size: number;
      resource_type: string;
      results: (
        QuickSearchClusterModel | QuickSearchInstanceModel | FaultOrRecycleMachineModel | TaskFlowModel | TicketModel
      )[];
    }>('/apis/quick_search/search_result/', params)
    .then((res) => ({
      ...res,
      results: res.results.map((item) => {
        if (res.resource_type === 'cluster') {
          return new QuickSearchClusterModel(item as QuickSearchClusterModel);
        }
        if (res.resource_type === 'instance') {
          return new QuickSearchInstanceModel(item as QuickSearchInstanceModel);
        }
        if (res.resource_type === 'machine') {
          return new FaultOrRecycleMachineModel(item as FaultOrRecycleMachineModel);
        }
        if (res.resource_type === 'task') {
          return new TaskFlowModel(item as TaskFlowModel);
        }
        if (res.resource_type === 'ticket') {
          return new TicketModel(item as TicketModel);
        }
        return item;
      }),
    }));
}
