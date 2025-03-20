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

import { getTicketsCount } from '@services/source/ticket';

export const useMenu = defineStore('useMenu', {
  state: () => ({
    hoverCollapsed: true,
    menuCountMap: {
      tickets: 0,
      todos: 0,
    },
    toggleCollapsed: false,
  }),
  getters: {
    // 切换展开/收起
    collapsed: (state) => state.toggleCollapsed && state.hoverCollapsed,
    // 处于 hover 展开
    isHover: (state) => state.toggleCollapsed && state.hoverCollapsed === false,
  },
  actions: {
    fetchTicketsCount() {
      getTicketsCount({ count_type: 'MY_APPROVE' }).then((count = 0) => {
        this.menuCountMap.tickets = count;
      });
    },
    fetchTodosCount() {
      getTicketsCount({ count_type: 'MY_TODO' }).then((count = 0) => {
        this.menuCountMap.todos = count;
      });
    },
    mouseenter() {
      this.hoverCollapsed = false;
    },
    mouseleave() {
      this.hoverCollapsed = true;
    },
    toggle() {
      this.toggleCollapsed = !this.toggleCollapsed;
    },
    updateMenuCount() {
      this.fetchTicketsCount();
      this.fetchTodosCount();
    },
  },
});
