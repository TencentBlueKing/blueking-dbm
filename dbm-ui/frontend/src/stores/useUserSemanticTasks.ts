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

import { acceptHMRUpdate, defineStore } from 'pinia';

import { getTicketsCount } from '@services/ticket';

export const useMenu = defineStore('useMenu', {
  state: () => ({
    toggleCollapsed: false,
    hoverCollapsed: true,
    menuCountMap: {
      todos: 0,
      tickets: 0,
    },
  }),
  getters: {
    // 切换展开/收起
    collapsed: state => state.toggleCollapsed && state.hoverCollapsed,
    // 处于 hover 展开
    isHover: state => state.toggleCollapsed && (state.hoverCollapsed === false),
  },
  actions: {
    toggle() {
      this.toggleCollapsed = !this.toggleCollapsed;
    },
    mouseenter() {
      this.hoverCollapsed = false;
    },
    mouseleave() {
      this.hoverCollapsed = true;
    },
    fetchTodosCount() {
      getTicketsCount('MY_TODO').then((count = 0) => {
        this.menuCountMap.todos = count;
      });
    },
    fetchTicketsCount() {
      getTicketsCount('MY_APPROVE').then((count = 0) => {
        this.menuCountMap.tickets = count;
      });
    },
    updateMenuCount() {
      this.fetchTicketsCount();
      this.fetchTodosCount();
    },
  },
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useMenu, import.meta.hot));
}
