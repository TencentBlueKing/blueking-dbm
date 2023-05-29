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
  <BkResizeLayout
    :border="false"
    class="influxdb-wrapper"
    collapsible
    disabled
    :initial-divide="320"
    :max="420"
    :min="320">
    <template #aside>
      <GroupList />
    </template>
    <template #main>
      <InstanceList />
    </template>
  </BkResizeLayout>
</template>

<script setup lang="ts">
  import mitt from 'mitt';

  import GroupList from './components/GroupList.vue';
  import InstanceList from './components/InstanceList.vue';

  import { useMainViewStore } from '@/stores';

  const eventBus = mitt();
  provide('eventBus', eventBus);

  const mainViewStore = useMainViewStore();
  mainViewStore.hasPadding = false;
</script>

<style lang="less" scoped>
.influxdb-wrapper {
  height: 100%;

  :deep(.bk-resize-layout-aside) {
    border: 0;

    &::after {
      display: none;
    }
  }
}
</style>
