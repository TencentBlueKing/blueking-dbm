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
  <div class="my-tickets-page">
    <List v-model="activeTicketId" />
    <div
      v-if="activeTicketId"
      class="ticket-detail-wrapper">
      <Details :ticket-id="activeTicketId" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { watch } from 'vue';

  import { useUrlSearch } from '@hooks';

  import Details from './components/details/Index.vue';
  import List from './components/list/Index.vue';

  const { appendSearchParams } = useUrlSearch();

  const activeTicketId = ref(0);

  watch(activeTicketId, () => {
    appendSearchParams({
      viewId: activeTicketId.value,
    });
  });
</script>
<style lang="less">
  .my-tickets-page {
    display: flex;
    height: 100%;

    .ticket-detail-wrapper {
      position: relative;
      height: 100%;
      flex: 1;
      overflow-y: auto;
    }
  }
</style>
