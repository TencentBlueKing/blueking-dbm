<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <MainView>
    <template #menu>
      <BkMenu
        :active-key="activeKey"
        :collapse="menuStore.collapsed"
        @click="handleChangeMenu"
        @mouseenter="menuStore.mouseenter"
        @mouseleave="menuStore.mouseleave">
        <div class="main-menu__list db-scroll-y">
          <BkMenuItem key="SelfServiceApply">
            <template #icon>
              <i class="db-icon-template" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ $t('服务申请') }}
            </span>
          </BkMenuItem>
          <BkMenuItem key="SelfServiceMyTickets">
            <template #icon>
              <i class="db-icon-ticket" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ $t('我的服务单') }}
            </span>
            <!-- <span class="main-menu__count">{{ menuStore.menuCountMap.tickets }}</span> -->
          </BkMenuItem>
          <BkMenuItem key="MyTodos">
            <template #icon>
              <i class="db-icon-todos" />
            </template>
            <span
              v-overflow-tips.right
              class="text-overflow">
              {{ $t('我的待办') }}
            </span>
            <span class="main-menu__count">{{ menuStore.menuCountMap.todos }}</span>
          </BkMenuItem>
        </div>
        <MenuToggleIcon />
      </BkMenu>
    </template>
  </MainView>
</template>

<script setup lang="ts">
  import { useMenu } from '@stores';

  import MainView from '@components/layouts/MainView.vue';

  import { useTimeoutPoll } from '@vueuse/core';

  import MenuToggleIcon from '../components/MenuToggleIcon.vue';
  import { useMenuInfo } from '../hooks/useMenuInfo';

  const menuStore = useMenu();
  const { activeKey, handleChangeMenu } = useMenuInfo();
  const { resume, pause } = useTimeoutPoll(menuStore.updateMenuCount, 10000);
  resume();

  onBeforeUnmount(() => {
    pause();
  });
</script>
