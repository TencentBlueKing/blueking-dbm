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
    class="dumper-instance-page"
    collapsible
    disabled
    :initial-divide="320"
    :max="420"
    :min="320">
    <template #aside>
      <RenderGroup @change="handleChangeGroup" />
    </template>
    <template #main>
      <RenderList :data="activeGroup" />
    </template>
  </BkResizeLayout>
</template>

<script setup lang="ts">
  import { listDumperConfig } from '@services/source/dumper';

  import RenderGroup from './components/render-group/Index.vue';
  import RenderList from './components/render-list/Index.vue';

  type DumperConfig = ServiceReturnType<typeof listDumperConfig>['results'][number];

  const activeGroup = ref<DumperConfig | null>(null);

  const handleChangeGroup = (group: DumperConfig | null) => {
    activeGroup.value = group;
  };
</script>

<style lang="less">
  .dumper-instance-page {
    height: 100%;

    .bk-resize-layout-aside {
      border: 0;

      &::after {
        display: none;
      }
    }
  }
</style>
