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
  <BkTable
    :pagination-heihgt="60"
    show-overflow-tooltip
    v-bind="$attrs">
    <slot />
    <template #empty>
      <slot name="empty">
        <EmptyStatus
          :is-anomalies="isAnomalies"
          :is-searching="isSearching"
          @clear-search="handleClearSearch"
          @refresh="handleRefresh" />
      </slot>
    </template>
  </BkTable>
</template>

<script setup lang="ts">
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  interface Emits {
    (e: 'refresh'): void,
    (e: 'clearSearch'): void
  }
  interface Props {
    isAnomalies?: boolean,
    isSearching?: boolean,
  }

  withDefaults(defineProps<Props>(), {
    isAnomalies: false,
    isSearching: false,
  });

  const emits = defineEmits<Emits>();

  const handleRefresh = () => emits('refresh');
  const handleClearSearch = () => emits('clearSearch');
</script>
