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
  <div class="my-tickets">
    <TicketList @change="handleChangeTicket" />
    <div
      v-if="activeTicket?.id"
      class="my-tickets__details db-scroll-y">
      <TicketDetails :data="activeTicket">
        <template #flows="{data}">
          <TicketFlows :data="data" />
        </template>
      </TicketDetails>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { TicketItem } from '@services/types/ticket';

  import { useMainViewStore } from '@stores';

  import TicketDetails from '../components/TicketDetails.vue';

  import TicketFlows from './components/TicketFlows.vue';
  import TicketList from './TicketList.vue';

  // 设置主视图布局不开启边距
  const mainViewStore = useMainViewStore();
  mainViewStore.hasPadding = false;

  const activeTicket = ref<TicketItem | null>(null);

  function handleChangeTicket(data: TicketItem | null) {
    activeTicket.value = data;
  }
</script>

<style lang="less" scoped>
.my-tickets {
  display: flex;
  height: 100%;

  &__details {
    flex: 1;
    height: 100%;
  }
}
</style>
