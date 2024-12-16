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
import QuickSearchEntryModel from '@services/model/quiker-search/quick-search-entry';
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
  resource_types: string[];
  filter_type: string;
  keyword?: string;
  short_code?: string;
  limit?: number;
}) {
  return http
    .post<{
      entry: QuickSearchEntryModel[];
      instance: QuickSearchInstanceModel[];
      resource_pool: DbResourceModel[];
      task: TaskFlowModel[];
      ticket: TicketModel<unknown>[];
      keyword: string;
      short_code: string;
    }>('/apis/quick_search/search/', params)
    .then((res) => ({
      ...res,
      entry: (res.entry || []).map((item) => new QuickSearchEntryModel(item)),
      instance: (res.instance || []).map((item) => new QuickSearchInstanceModel(item)),
      resource_pool: (res.resource_pool || []).map((item) => new DbResourceModel(item)),
      task: (res.task || []).map((item) => new TaskFlowModel(item)),
      ticket: (res.ticket || []).map((item) => new TicketModel(item)),
    }));
}
