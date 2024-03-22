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

import { defineStore } from 'pinia';

import TicketModel from '@services/model/ticket/ticket';

import { generateCloneData } from './generateCloneData';

interface State {
  ticketType: string;
  cloneData: unknown;
}

export const useTicketCloneInfo = defineStore('useTicketCloneInfo', {
  state: (): State => ({
    ticketType: '',
    cloneData: undefined,
  }),
  actions: {
    async update(ticketData?: TicketModel) {
      if (!ticketData) {
        // 初始化数据
        this.$patch({
          ticketType: '',
          cloneData: undefined,
        });
        return;
      }

      // 更新数据
      const ticketType = ticketData.ticket_type;
      const cloneData = await generateCloneData(ticketData);
      this.$patch({
        ticketType,
        cloneData,
      });
    },
  },
});
